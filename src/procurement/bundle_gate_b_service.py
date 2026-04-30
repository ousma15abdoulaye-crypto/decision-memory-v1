"""Controlled Gate B role evaluation for existing supplier_bundles."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from src.assembler.graph import _check_completeness
from src.db import db_execute, db_execute_one, db_fetchall, get_connection

logger = logging.getLogger(__name__)

SERVICE_NAME = "bundle_gate_b_service"
SCORABLE_GATE_B_ROLE = "scorable"
QUALIFIED_STATUS = "qualified"
PENDING_STATUS = "pending"


class BundleGateBRole(StrEnum):
    SCORABLE = "scorable"
    REFERENCE = "reference"
    INTERNAL = "internal"
    UNUSABLE = "unusable"


class BundleGateBQualificationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    SKIPPED_ALREADY_EVALUATED = "SKIPPED_ALREADY_EVALUATED"
    BUNDLE_NOT_FOUND = "BUNDLE_NOT_FOUND"
    WORKSPACE_MISMATCH = "WORKSPACE_MISMATCH"
    DOCUMENTS_MISSING = "DOCUMENTS_MISSING"
    RAW_TEXT_MISSING = "RAW_TEXT_MISSING"
    M12_MISSING = "M12_MISSING"


@dataclass(frozen=True)
class BundleGateBQualificationResult:
    status: BundleGateBQualificationStatus
    workspace_id: str
    bundle_id: str
    vendor_name_raw: str | None = None
    gate_b_role: str | None = None
    gate_b_reason_codes: list[str] = field(default_factory=list)
    qualification_status: str | None = None
    completeness_score: float | None = None
    missing_documents: list[str] = field(default_factory=list)
    doc_count: int = 0
    docs_with_text: int = 0
    docs_with_m12: int = 0
    updated: bool = False
    error: str | None = None

    def log_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "workspace_id": self.workspace_id,
            "bundle_id": self.bundle_id,
            "vendor_name_raw": self.vendor_name_raw,
            "gate_b_role": self.gate_b_role,
            "gate_b_reason_codes": list(self.gate_b_reason_codes),
            "qualification_status": self.qualification_status,
            "completeness_score": self.completeness_score,
            "missing_documents": list(self.missing_documents),
            "doc_count": self.doc_count,
            "docs_with_text": self.docs_with_text,
            "docs_with_m12": self.docs_with_m12,
            "updated": self.updated,
            "error": self.error,
        }


def _qualification_status_for_gate_b(gate_b_role: str) -> str:
    if gate_b_role == SCORABLE_GATE_B_ROLE:
        return QUALIFIED_STATUS
    return PENDING_STATUS


def _docs_with_text(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if str(r.get("raw_text") or "").strip()]


def _docs_with_m12(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if str(r.get("m12_doc_kind") or "").strip()]


def _rows_for_completeness(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        doc = dict(row)
        doc["doc_type"] = doc.get("m12_doc_kind") or doc.get("doc_type")
        normalized.append(doc)
    return normalized


def _reason_codes(reason: str) -> list[str]:
    return [reason] if reason else []


def _build_evidence(
    rows: list[dict[str, Any]],
    *,
    gate_b_role: str,
    gate_b_reason_codes: list[str],
    completeness_score: float,
    missing_documents: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "source": "gate_b_classify_bundle_for_m14",
            "gate_b_role": gate_b_role,
            "gate_b_reason_codes": list(gate_b_reason_codes),
            "doc_count": len(rows),
            "docs_with_text": len(_docs_with_text(rows)),
            "docs_with_m12": len(_docs_with_m12(rows)),
            "doc_types": sorted({str(r.get("doc_type") or "") for r in rows}),
            "m12_doc_kinds": sorted(
                {
                    str(r.get("m12_doc_kind") or "")
                    for r in rows
                    if r.get("m12_doc_kind")
                }
            ),
            "completeness_score": completeness_score,
            "missing_documents": list(missing_documents),
        }
    ]


def qualify_supplier_bundle_gate_b(
    workspace_id: UUID,
    bundle_id: UUID,
    force: bool = False,
) -> BundleGateBQualificationResult:
    """Persist a V1.1 Gate B role for one existing supplier_bundle.

    This service does not score, run M14, build matrices, delete rows, or mutate
    document extraction/classification data.
    """
    workspace_id_str = str(workspace_id)
    bundle_id_str = str(bundle_id)

    with get_connection() as conn:
        bundle = db_execute_one(
            conn,
            """
            SELECT id::text AS id,
                   workspace_id::text AS workspace_id,
                   vendor_name_raw,
                   gate_b_role,
                   gate_b_reason_codes,
                   qualification_status,
                   completeness_score,
                   missing_documents
            FROM supplier_bundles
            WHERE id = CAST(:bundle_id AS uuid)
            """,
            {"bundle_id": bundle_id_str},
        )
        if not bundle:
            return BundleGateBQualificationResult(
                status=BundleGateBQualificationStatus.BUNDLE_NOT_FOUND,
                workspace_id=workspace_id_str,
                bundle_id=bundle_id_str,
            )
        if str(bundle["workspace_id"]) != workspace_id_str:
            return BundleGateBQualificationResult(
                status=BundleGateBQualificationStatus.WORKSPACE_MISMATCH,
                workspace_id=workspace_id_str,
                bundle_id=bundle_id_str,
                vendor_name_raw=str(bundle.get("vendor_name_raw") or ""),
            )

        existing_role = str(bundle.get("gate_b_role") or "").strip().lower()
        if existing_role and not force:
            return BundleGateBQualificationResult(
                status=BundleGateBQualificationStatus.SKIPPED_ALREADY_EVALUATED,
                workspace_id=workspace_id_str,
                bundle_id=bundle_id_str,
                vendor_name_raw=str(bundle.get("vendor_name_raw") or ""),
                gate_b_role=existing_role,
                gate_b_reason_codes=list(bundle.get("gate_b_reason_codes") or []),
                qualification_status=bundle.get("qualification_status"),
                completeness_score=(
                    float(bundle["completeness_score"])
                    if bundle.get("completeness_score") is not None
                    else None
                ),
                missing_documents=list(bundle.get("missing_documents") or []),
                updated=False,
            )

        rows = db_fetchall(
            conn,
            """
            SELECT id::text AS id,
                   doc_type::text AS doc_type,
                   doc_role::text AS doc_role,
                   filename,
                   raw_text,
                   m12_doc_kind,
                   m12_confidence,
                   bundle_id::text AS bundle_id
            FROM bundle_documents
            WHERE bundle_id = CAST(:bundle_id AS uuid)
              AND workspace_id = CAST(:workspace_id AS uuid)
            ORDER BY uploaded_at NULLS LAST, id::text
            """,
            {"bundle_id": bundle_id_str, "workspace_id": workspace_id_str},
        )

        doc_count = len(rows or [])
        if doc_count == 0:
            return BundleGateBQualificationResult(
                status=BundleGateBQualificationStatus.DOCUMENTS_MISSING,
                workspace_id=workspace_id_str,
                bundle_id=bundle_id_str,
                vendor_name_raw=str(bundle.get("vendor_name_raw") or ""),
                error="bundle_documents_required_for_gate_b",
            )

        text_rows = _docs_with_text(rows)
        if not text_rows:
            return BundleGateBQualificationResult(
                status=BundleGateBQualificationStatus.RAW_TEXT_MISSING,
                workspace_id=workspace_id_str,
                bundle_id=bundle_id_str,
                vendor_name_raw=str(bundle.get("vendor_name_raw") or ""),
                doc_count=doc_count,
                error="raw_text_required_for_gate_b",
            )

        m12_rows = _docs_with_m12(rows)
        if len(m12_rows) < len(text_rows):
            return BundleGateBQualificationResult(
                status=BundleGateBQualificationStatus.M12_MISSING,
                workspace_id=workspace_id_str,
                bundle_id=bundle_id_str,
                vendor_name_raw=str(bundle.get("vendor_name_raw") or ""),
                doc_count=doc_count,
                docs_with_text=len(text_rows),
                docs_with_m12=len(m12_rows),
                error="m12_doc_kind_required_for_text_documents",
            )

        completeness_score, missing_documents = _check_completeness(
            _rows_for_completeness(rows)
        )

        from src.services.pipeline_v5_service import gate_b_classify_bundle_for_m14

        role_upper, reason = gate_b_classify_bundle_for_m14(rows)
        gate_b_role = role_upper.lower()
        gate_b_reason_codes = _reason_codes(reason)
        qualification_status = _qualification_status_for_gate_b(gate_b_role)
        evidence = _build_evidence(
            rows,
            gate_b_role=gate_b_role,
            gate_b_reason_codes=gate_b_reason_codes,
            completeness_score=completeness_score,
            missing_documents=missing_documents,
        )

        db_execute(
            conn,
            """
            UPDATE supplier_bundles
            SET gate_b_role = :gate_b_role,
                gate_b_reason_codes = :gate_b_reason_codes,
                gate_b_evidence = CAST(:gate_b_evidence AS jsonb),
                gate_b_evaluated_at = :gate_b_evaluated_at,
                gate_b_evaluated_by = :gate_b_evaluated_by,
                qualification_status = :qualification_status,
                completeness_score = :completeness_score,
                missing_documents = :missing_documents
            WHERE id = CAST(:bundle_id AS uuid)
              AND workspace_id = CAST(:workspace_id AS uuid)
            """,
            {
                "gate_b_role": gate_b_role,
                "gate_b_reason_codes": gate_b_reason_codes,
                "gate_b_evidence": json.dumps(evidence, ensure_ascii=False),
                "gate_b_evaluated_at": datetime.now(UTC),
                "gate_b_evaluated_by": SERVICE_NAME,
                "qualification_status": qualification_status,
                "completeness_score": completeness_score,
                "missing_documents": missing_documents,
                "bundle_id": bundle_id_str,
                "workspace_id": workspace_id_str,
            },
        )

    logger.info(
        "[GATE-B-BUNDLE] workspace=%s bundle=%s role=%s reasons=%s qualification=%s",
        workspace_id_str,
        bundle_id_str,
        gate_b_role,
        ",".join(gate_b_reason_codes),
        qualification_status,
    )
    return BundleGateBQualificationResult(
        status=BundleGateBQualificationStatus.SUCCESS,
        workspace_id=workspace_id_str,
        bundle_id=bundle_id_str,
        vendor_name_raw=str(bundle.get("vendor_name_raw") or ""),
        gate_b_role=gate_b_role,
        gate_b_reason_codes=gate_b_reason_codes,
        qualification_status=qualification_status,
        completeness_score=completeness_score,
        missing_documents=missing_documents,
        doc_count=doc_count,
        docs_with_text=len(text_rows),
        docs_with_m12=len(m12_rows),
        updated=True,
    )
