"""
Pass 1D — Process Linking (L7, case-level).

Links documents within a procurement process. Operates at case level
when multiple documents are available; degrades gracefully to single-doc.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from src.annotation.pass_output import (
    AnnotationPassOutput,
    PassError,
    PassRunStatus,
)
from src.procurement.document_ontology import DocumentKindParent
from src.procurement.process_linker import (
    DocumentSummary,
    build_process_linking,
)

logger = logging.getLogger(__name__)

_PASS_NAME = "pass_1d_process_linking"
_PASS_VERSION = "1.0.0"


def _build_summary(doc_data: dict[str, Any]) -> DocumentSummary:
    """Build DocumentSummary from a Pass 1A m12_recognition dict."""
    recognition = doc_data.get("m12_recognition", {})

    doc_kind_str = recognition.get("document_kind", {}).get("value", "unknown")
    try:
        doc_kind = DocumentKindParent(doc_kind_str)
    except ValueError:
        doc_kind = DocumentKindParent.UNKNOWN

    return DocumentSummary(
        document_id=doc_data.get("document_id", ""),
        document_kind=doc_kind,
        procedure_reference=recognition.get("procedure_reference_detected", {}).get(
            "value"
        ),
        issuing_entity=recognition.get("issuing_entity_detected", {}).get("value"),
        project_name=recognition.get("project_name_detected", {}).get("value"),
        zones=recognition.get("zone_scope_detected", {}).get("value", []),
        submission_deadline=recognition.get("submission_deadline_detected", {}).get(
            "value"
        ),
    )


def run_pass_1d_process_linking(
    *,
    normalized_text: str,
    document_id: str,
    run_id: uuid.UUID,
    pass_1a_output_data: dict[str, Any],
    case_documents_1a: list[dict[str, Any]] | None = None,
) -> AnnotationPassOutput:
    """
    Execute Pass 1D: process linking.

    case_documents_1a: list of Pass 1A output_data dicts for all case documents.
    If None or empty, single-document mode.
    """
    started = datetime.now(UTC)
    errors: list[PassError] = []

    try:
        source_data = {**pass_1a_output_data, "document_id": document_id}
        source = _build_summary(source_data)

        candidates: list[DocumentSummary] = []
        if case_documents_1a:
            for cd in case_documents_1a:
                s = _build_summary(cd)
                if s.document_id != document_id:
                    candidates.append(s)

        linking = build_process_linking(source, candidates, normalized_text)

        output_data: dict[str, Any] = {
            "m12_linking": linking.model_dump(mode="json"),
            "process_role": linking.process_role.value,
            "linked_parents_count": len(linking.linked_parent_hint),
            "suppliers_detected_count": len(linking.suppliers_detected),
        }
        status = PassRunStatus.SUCCESS

    except Exception as exc:
        logger.exception("pass_1d_error")
        errors.append(PassError(code="PASS_1D_ERROR", message=str(exc)[:500]))
        status = PassRunStatus.FAILED
        output_data = {}

    completed = datetime.now(UTC)
    return AnnotationPassOutput(
        pass_name=_PASS_NAME,
        pass_version=_PASS_VERSION,
        document_id=document_id,
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        status=status,
        output_data=output_data,
        errors=errors,
        metadata={
            "duration_ms": int((completed - started).total_seconds() * 1000),
        },
    )
