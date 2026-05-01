"""Controlled bundle-level offer extraction for V1.1 M4B."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from src.couche_a.extraction.criterion import _OFFER_TYPE_TO_ROLE
from src.couche_a.extraction.offer_pipeline import extract_offer_content_async
from src.couche_a.extraction.persistence import persist_tdr_result_to_db
from src.db import db_execute_one, db_fetchall, get_connection

logger = logging.getLogger(__name__)

OFFER_DOC_KINDS = {
    "offer",
    "quotation",
    "vendor_offer",
    "offer_technical",
    "offer_financial",
    "offer_combined",
}


class BundleOfferExtractionStatus(StrEnum):
    SUCCESS = "SUCCESS"
    SKIPPED_ALREADY_EXTRACTED = "SKIPPED_ALREADY_EXTRACTED"
    BUNDLE_NOT_FOUND = "BUNDLE_NOT_FOUND"
    WORKSPACE_MISMATCH = "WORKSPACE_MISMATCH"
    NOT_SCORABLE = "NOT_SCORABLE"
    NO_DOCUMENTS = "NO_DOCUMENTS"
    RAW_TEXT_MISSING = "RAW_TEXT_MISSING"
    M12_MISSING = "M12_MISSING"
    NO_OFFER_DOCUMENT = "NO_OFFER_DOCUMENT"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    PERSISTENCE_FAILED = "PERSISTENCE_FAILED"


@dataclass(frozen=True)
class BundleOfferExtractionResult:
    status: BundleOfferExtractionStatus
    workspace_id: str
    bundle_id: str
    vendor_name_raw: str | None = None
    extraction_id: str | None = None
    supplier_name: str | None = None
    doc_count: int = 0
    offer_doc_count: int = 0
    raw_text_len: int = 0
    updated: bool = False
    error: str | None = None

    def log_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "workspace_id": self.workspace_id,
            "bundle_id": self.bundle_id,
            "vendor_name_raw": self.vendor_name_raw,
            "extraction_id": self.extraction_id,
            "supplier_name": self.supplier_name,
            "doc_count": self.doc_count,
            "offer_doc_count": self.offer_doc_count,
            "raw_text_len": self.raw_text_len,
            "updated": self.updated,
            "error": self.error,
        }


def _is_offer_document(row: dict[str, Any]) -> bool:
    m12 = str(row.get("m12_doc_kind") or "").strip().lower()
    doc_type = str(row.get("doc_type") or "").strip().lower()
    return m12 in OFFER_DOC_KINDS or doc_type in OFFER_DOC_KINDS


def _offer_type_for_rows(rows: list[dict[str, Any]]) -> str:
    kinds = {
        str(row.get("m12_doc_kind") or row.get("doc_type") or "").strip().lower()
        for row in rows
    }
    if "offer_financial" in kinds:
        return "financiere"
    return "technique"


async def extract_supplier_bundle_offer_async(
    workspace_id: UUID,
    bundle_id: UUID,
    force: bool = False,
) -> BundleOfferExtractionResult:
    """Extract one scorable supplier bundle into ``offer_extractions`` only.

    This service intentionally does not run M13, M14, bridge, scoring, matrices,
    or mutate raw_text, M12, Gate B, evaluation_documents, or criterion_assessments.
    """
    workspace_id_str = str(workspace_id)
    bundle_id_str = str(bundle_id)

    with get_connection() as conn:
        bundle = db_execute_one(
            conn,
            """
            SELECT sb.id::text AS id,
                   sb.workspace_id::text AS workspace_id,
                   sb.vendor_name_raw,
                   gate_b_role,
                   pw.legacy_case_id::text AS legacy_case_id
            FROM supplier_bundles sb
            JOIN process_workspaces pw
              ON pw.id = sb.workspace_id
            WHERE sb.id = CAST(:bundle_id AS uuid)
            """,
            {"bundle_id": bundle_id_str},
        )
        if not bundle:
            return BundleOfferExtractionResult(
                status=BundleOfferExtractionStatus.BUNDLE_NOT_FOUND,
                workspace_id=workspace_id_str,
                bundle_id=bundle_id_str,
            )
        if str(bundle["workspace_id"]) != workspace_id_str:
            return BundleOfferExtractionResult(
                status=BundleOfferExtractionStatus.WORKSPACE_MISMATCH,
                workspace_id=workspace_id_str,
                bundle_id=bundle_id_str,
                vendor_name_raw=str(bundle.get("vendor_name_raw") or ""),
            )
        if str(bundle.get("gate_b_role") or "").strip().lower() != "scorable":
            return BundleOfferExtractionResult(
                status=BundleOfferExtractionStatus.NOT_SCORABLE,
                workspace_id=workspace_id_str,
                bundle_id=bundle_id_str,
                vendor_name_raw=str(bundle.get("vendor_name_raw") or ""),
                error="gate_b_role_must_be_scorable",
            )

        existing = db_execute_one(
            conn,
            """
            SELECT id, supplier_name
            FROM offer_extractions
            WHERE workspace_id = CAST(:workspace_id AS uuid)
              AND bundle_id = CAST(:bundle_id AS uuid)
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"workspace_id": workspace_id_str, "bundle_id": bundle_id_str},
        )
        if existing and not force:
            return BundleOfferExtractionResult(
                status=BundleOfferExtractionStatus.SKIPPED_ALREADY_EXTRACTED,
                workspace_id=workspace_id_str,
                bundle_id=bundle_id_str,
                vendor_name_raw=str(bundle.get("vendor_name_raw") or ""),
                extraction_id=str(existing.get("id") or ""),
                supplier_name=existing.get("supplier_name"),
            )

        rows = db_fetchall(
            conn,
            """
            SELECT id::text AS id,
                   doc_type::text AS doc_type,
                   filename,
                   raw_text,
                   m12_doc_kind,
                   bundle_id::text AS bundle_id
            FROM bundle_documents
            WHERE bundle_id = CAST(:bundle_id AS uuid)
              AND workspace_id = CAST(:workspace_id AS uuid)
            ORDER BY uploaded_at NULLS LAST, id::text
            """,
            {"bundle_id": bundle_id_str, "workspace_id": workspace_id_str},
        )

    doc_count = len(rows or [])
    vendor_name = str(bundle.get("vendor_name_raw") or "")
    if doc_count == 0:
        return BundleOfferExtractionResult(
            status=BundleOfferExtractionStatus.NO_DOCUMENTS,
            workspace_id=workspace_id_str,
            bundle_id=bundle_id_str,
            vendor_name_raw=vendor_name,
            error="bundle_documents_required_for_offer_extraction",
        )

    text_rows = [r for r in rows if str(r.get("raw_text") or "").strip()]
    if not text_rows:
        return BundleOfferExtractionResult(
            status=BundleOfferExtractionStatus.RAW_TEXT_MISSING,
            workspace_id=workspace_id_str,
            bundle_id=bundle_id_str,
            vendor_name_raw=vendor_name,
            doc_count=doc_count,
            error="raw_text_required_for_offer_extraction",
        )

    if any(not str(r.get("m12_doc_kind") or "").strip() for r in text_rows):
        return BundleOfferExtractionResult(
            status=BundleOfferExtractionStatus.M12_MISSING,
            workspace_id=workspace_id_str,
            bundle_id=bundle_id_str,
            vendor_name_raw=vendor_name,
            doc_count=doc_count,
            error="m12_doc_kind_required_for_text_documents",
        )

    offer_rows = [r for r in text_rows if _is_offer_document(r)]
    if not offer_rows:
        return BundleOfferExtractionResult(
            status=BundleOfferExtractionStatus.NO_OFFER_DOCUMENT,
            workspace_id=workspace_id_str,
            bundle_id=bundle_id_str,
            vendor_name_raw=vendor_name,
            doc_count=doc_count,
            error="offer_document_required_for_offer_extraction",
        )

    text = "\n\n".join(str(r.get("raw_text") or "").strip() for r in offer_rows)
    offer_type = _offer_type_for_rows(offer_rows)
    document_role = _OFFER_TYPE_TO_ROLE.get(offer_type, "technical_offer")
    case_id = str(bundle.get("legacy_case_id") or workspace_id_str)

    try:
        extraction = await extract_offer_content_async(
            document_id=bundle_id_str,
            text=text,
            document_role=document_role,
        )
    except Exception as exc:
        logger.exception(
            "[BUNDLE-OFFER-EXTRACT] extraction failed bundle=%s", bundle_id_str
        )
        return BundleOfferExtractionResult(
            status=BundleOfferExtractionStatus.EXTRACTION_FAILED,
            workspace_id=workspace_id_str,
            bundle_id=bundle_id_str,
            vendor_name_raw=vendor_name,
            doc_count=doc_count,
            offer_doc_count=len(offer_rows),
            raw_text_len=len(text),
            error=type(exc).__name__,
        )

    if not getattr(extraction, "extraction_ok", False):
        return BundleOfferExtractionResult(
            status=BundleOfferExtractionStatus.EXTRACTION_FAILED,
            workspace_id=workspace_id_str,
            bundle_id=bundle_id_str,
            vendor_name_raw=vendor_name,
            doc_count=doc_count,
            offer_doc_count=len(offer_rows),
            raw_text_len=len(text),
            error=str(getattr(extraction, "error_reason", "") or "extraction_not_ok"),
        )

    try:
        persist_tdr_result_to_db(
            extraction,
            case_id,
            bundle_id_str,
            workspace_id=workspace_id_str,
        )
        with get_connection() as conn:
            saved = db_execute_one(
                conn,
                """
                SELECT id, supplier_name
                FROM offer_extractions
                WHERE workspace_id = CAST(:workspace_id AS uuid)
                  AND bundle_id = CAST(:bundle_id AS uuid)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                {"workspace_id": workspace_id_str, "bundle_id": bundle_id_str},
            )
    except Exception as exc:
        logger.exception(
            "[BUNDLE-OFFER-EXTRACT] persistence failed bundle=%s", bundle_id_str
        )
        return BundleOfferExtractionResult(
            status=BundleOfferExtractionStatus.PERSISTENCE_FAILED,
            workspace_id=workspace_id_str,
            bundle_id=bundle_id_str,
            vendor_name_raw=vendor_name,
            doc_count=doc_count,
            offer_doc_count=len(offer_rows),
            raw_text_len=len(text),
            error=type(exc).__name__,
        )

    logger.info(
        "[BUNDLE-OFFER-EXTRACT] workspace=%s bundle=%s status=SUCCESS extraction_id=%s",
        workspace_id_str,
        bundle_id_str,
        (saved or {}).get("id"),
    )
    return BundleOfferExtractionResult(
        status=BundleOfferExtractionStatus.SUCCESS,
        workspace_id=workspace_id_str,
        bundle_id=bundle_id_str,
        vendor_name_raw=vendor_name,
        extraction_id=str((saved or {}).get("id") or ""),
        supplier_name=(saved or {}).get("supplier_name"),
        doc_count=doc_count,
        offer_doc_count=len(offer_rows),
        raw_text_len=len(text),
        updated=True,
    )


def extract_supplier_bundle_offer(
    workspace_id: UUID,
    bundle_id: UUID,
    force: bool = False,
) -> BundleOfferExtractionResult:
    """Synchronous wrapper for tests and non-async callers."""
    return asyncio.run(
        extract_supplier_bundle_offer_async(
            workspace_id=workspace_id,
            bundle_id=bundle_id,
            force=force,
        )
    )
