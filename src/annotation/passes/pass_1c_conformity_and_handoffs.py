"""
Pass 1C — Conformity Signal + Handoffs (L6 + H1/H2/H3).

Produces document-level conformity status and structured handoff payloads.
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
from src.procurement.document_conformity_signal import compute_conformity_signal
from src.procurement.document_ontology import (
    SOURCE_RULES_KINDS,
    DocumentKindParent,
    ProcurementFamily,
    ProcurementFamilySub,
    ProcurementFramework,
)
from src.procurement.eligibility_gate_extractor import extract_eligibility_gates
from src.procurement.handoff_builder import build_handoffs
from src.procurement.procedure_models import (
    DocumentValidity,
)
from src.procurement.scoring_structure_extractor import extract_scoring_structure

logger = logging.getLogger(__name__)

_PASS_NAME = "pass_1c_conformity_and_handoffs"
_PASS_VERSION = "1.0.0"


def run_pass_1c_conformity_and_handoffs(
    *,
    normalized_text: str,
    document_id: str,
    run_id: uuid.UUID,
    document_kind_str: str,
    is_composite: str,
    validity_dict: dict[str, Any],
    framework_str: str,
    framework_confidence: float,
    family_str: str,
    family_sub_str: str,
) -> AnnotationPassOutput:
    """Execute Pass 1C: conformity signal + eligibility gates + scoring + handoffs."""
    started = datetime.now(UTC)
    errors: list[PassError] = []

    try:
        doc_kind = DocumentKindParent(document_kind_str)
    except ValueError:
        doc_kind = DocumentKindParent.UNKNOWN

    try:
        framework = ProcurementFramework(framework_str)
    except ValueError:
        framework = ProcurementFramework.UNKNOWN

    try:
        family = ProcurementFamily(family_str)
    except ValueError:
        family = ProcurementFamily.UNKNOWN

    try:
        family_sub = ProcurementFamilySub(family_sub_str)
    except ValueError:
        family_sub = ProcurementFamilySub.GENERIC

    try:
        validity = DocumentValidity.model_validate(validity_dict)

        # L6: conformity signal
        conformity = compute_conformity_signal(doc_kind, is_composite, validity)

        # L6 sub: eligibility gates (only for source_rules)
        gates = []
        if doc_kind in SOURCE_RULES_KINDS:
            gates = extract_eligibility_gates(normalized_text)
            conformity.eligibility_gates_extracted = gates

        # L6 sub: scoring structure (only for source_rules)
        scoring = None
        if doc_kind in SOURCE_RULES_KINDS:
            scoring = extract_scoring_structure(normalized_text)
            conformity.scoring_structure_extracted = scoring

        # H1/H2/H3 handoffs
        handoffs = build_handoffs(
            doc_kind,
            framework,
            framework_confidence,
            family,
            family_sub,
            gates,
            scoring,
            normalized_text,
        )

        output_data: dict[str, Any] = {
            "m12_conformity": conformity.model_dump(mode="json"),
            "m12_handoffs": handoffs.model_dump(mode="json"),
            "conformity_status": conformity.document_conformity_status.value,
        }
        status = PassRunStatus.SUCCESS

    except Exception as exc:
        logger.exception("pass_1c_error")
        errors.append(PassError(code="PASS_1C_ERROR", message=str(exc)[:500]))
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
