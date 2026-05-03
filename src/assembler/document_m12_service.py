"""Document-level M12 classification for existing bundle_documents."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID

from src.assembler.graph import classify_document_type_for_pass_minus_one
from src.db import db_execute, db_execute_one, get_connection

logger = logging.getLogger(__name__)


class M12ClassificationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    SKIPPED_ALREADY_CLASSIFIED = "SKIPPED_ALREADY_CLASSIFIED"
    RAW_TEXT_MISSING = "RAW_TEXT_MISSING"
    WORKSPACE_MISMATCH = "WORKSPACE_MISMATCH"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"


@dataclass(frozen=True)
class M12ClassificationResult:
    status: M12ClassificationStatus
    workspace_id: str
    document_id: str
    raw_text_len: int = 0
    m12_doc_kind: str | None = None
    m12_confidence: float | None = None
    m12_evidence: list[str] = field(default_factory=list)
    updated: bool = False
    error: str | None = None

    def log_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "workspace_id": self.workspace_id,
            "document_id": self.document_id,
            "raw_text_len": self.raw_text_len,
            "m12_doc_kind": self.m12_doc_kind,
            "m12_confidence": self.m12_confidence,
            "m12_evidence": list(self.m12_evidence),
            "updated": self.updated,
            "error": self.error,
        }


def _build_evidence(filename: str, raw_text_len: int, doc_kind: str) -> list[str]:
    return [
        "source=classify_document_type_for_pass_minus_one",
        f"filename={filename}",
        f"raw_text_len={raw_text_len}",
        f"matched_doc_kind={doc_kind}",
    ]


def classify_bundle_document_m12(
    document_id: UUID,
    workspace_id: UUID,
    force: bool = False,
) -> M12ClassificationResult:
    """Classify one existing bundle_document through the existing Pass-1 M12 rule.

    The service intentionally updates only M12 columns. It never rewrites raw_text,
    bundle state, scoring data, matrices, or source files.
    """
    document_id_str = str(document_id)
    workspace_id_str = str(workspace_id)

    with get_connection() as conn:
        row = db_execute_one(
            conn,
            """
            SELECT id::text AS id,
                   workspace_id::text AS workspace_id,
                   filename,
                   raw_text,
                   m12_doc_kind,
                   m12_confidence,
                   m12_evidence
            FROM bundle_documents
            WHERE id = CAST(:document_id AS uuid)
            """,
            {"document_id": document_id_str},
        )

        if not row:
            return M12ClassificationResult(
                status=M12ClassificationStatus.DOCUMENT_NOT_FOUND,
                workspace_id=workspace_id_str,
                document_id=document_id_str,
            )

        if str(row["workspace_id"]) != workspace_id_str:
            return M12ClassificationResult(
                status=M12ClassificationStatus.WORKSPACE_MISMATCH,
                workspace_id=workspace_id_str,
                document_id=document_id_str,
            )

        existing_kind = row.get("m12_doc_kind")
        raw_text = row.get("raw_text") if isinstance(row.get("raw_text"), str) else ""
        raw_text_len = len(raw_text or "")

        if existing_kind and not force:
            return M12ClassificationResult(
                status=M12ClassificationStatus.SKIPPED_ALREADY_CLASSIFIED,
                workspace_id=workspace_id_str,
                document_id=document_id_str,
                raw_text_len=raw_text_len,
                m12_doc_kind=str(existing_kind),
                m12_confidence=(
                    float(row["m12_confidence"])
                    if row.get("m12_confidence") is not None
                    else None
                ),
                m12_evidence=list(row.get("m12_evidence") or []),
                updated=False,
            )

        if not raw_text.strip():
            return M12ClassificationResult(
                status=M12ClassificationStatus.RAW_TEXT_MISSING,
                workspace_id=workspace_id_str,
                document_id=document_id_str,
                raw_text_len=raw_text_len,
                error="raw_text_required_for_m12_document_classification",
            )

        filename = str(row.get("filename") or "")
        doc_kind = classify_document_type_for_pass_minus_one(raw_text, filename)
        confidence = 0.8
        evidence = _build_evidence(filename, raw_text_len, doc_kind)

        db_execute(
            conn,
            """
            UPDATE bundle_documents
            SET m12_doc_kind = :m12_doc_kind,
                m12_confidence = :m12_confidence,
                m12_evidence = :m12_evidence
            WHERE id = CAST(:document_id AS uuid)
              AND workspace_id = CAST(:workspace_id AS uuid)
            """,
            {
                "m12_doc_kind": doc_kind,
                "m12_confidence": confidence,
                "m12_evidence": evidence,
                "document_id": document_id_str,
                "workspace_id": workspace_id_str,
            },
        )

    logger.info(
        "[M12-DOC] bundle_document workspace=%s document=%s status=%s kind=%s conf=%.2f",
        workspace_id_str,
        document_id_str,
        M12ClassificationStatus.SUCCESS.value,
        doc_kind,
        confidence,
    )
    return M12ClassificationResult(
        status=M12ClassificationStatus.SUCCESS,
        workspace_id=workspace_id_str,
        document_id=document_id_str,
        raw_text_len=raw_text_len,
        m12_doc_kind=doc_kind,
        m12_confidence=confidence,
        m12_evidence=evidence,
        updated=True,
    )
