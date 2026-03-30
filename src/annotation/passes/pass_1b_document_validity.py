"""
Pass 1B — Document Validity (L4 + L5).

Detects mandatory parts and computes document validity.
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
from src.procurement.document_validity_rules import compute_validity
from src.procurement.mandatory_parts_engine import MandatoryPartsEngine

logger = logging.getLogger(__name__)

_PASS_NAME = "pass_1b_document_validity"
_PASS_VERSION = "1.0.0"

_mp_engine: MandatoryPartsEngine | None = None


def _get_engine() -> MandatoryPartsEngine:
    global _mp_engine
    if _mp_engine is None:
        _mp_engine = MandatoryPartsEngine()
    return _mp_engine


def run_pass_1b_document_validity(
    *,
    normalized_text: str,
    document_id: str,
    run_id: uuid.UUID,
    document_kind: str,
    quality_class: str = "good",
) -> AnnotationPassOutput:
    """Execute Pass 1B: mandatory parts detection + validity judgment."""
    started = datetime.now(UTC)
    errors: list[PassError] = []

    try:
        engine = _get_engine()
        detection_details, optional_present, not_applicable = engine.detect_parts(
            normalized_text, document_kind
        )
        validity = compute_validity(
            detection_details,
            optional_present,
            not_applicable,
            document_kind,
            quality_class,
        )

        output_data: dict[str, Any] = {
            "m12_validity": validity.model_dump(mode="json"),
            "document_kind": document_kind,
            "validity_status": validity.document_validity_status.value,
            "mandatory_coverage": validity.mandatory_coverage,
            "mandatory_parts_present": validity.mandatory_parts_present,
            "mandatory_parts_missing": validity.mandatory_parts_missing,
        }
        status = PassRunStatus.SUCCESS
        if validity.document_validity_status.value in ("invalid", "not_assessable"):
            status = PassRunStatus.DEGRADED

    except Exception as exc:
        logger.exception("pass_1b_error")
        errors.append(PassError(code="PASS_1B_ERROR", message=str(exc)[:500]))
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
            "quality_class": quality_class,
        },
    )
