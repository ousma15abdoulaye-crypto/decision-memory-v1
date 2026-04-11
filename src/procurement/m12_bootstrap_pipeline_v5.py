"""
M12 minimal pour Pipeline V5 — bootstrap déterministe vers M13.

Extrait de ``pipeline_v5_service`` pour tests unitaires et réutilisation sans
coupler au routeur HTTP.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from src.procurement.document_ontology import (
    DocumentKindParent,
    DocumentLayer,
    DocumentStage,
    ProcedureType,
    ProcessRole,
    ProcurementFamily,
    ProcurementFamilySub,
    ProcurementFramework,
)
from src.procurement.handoff_builder import build_handoffs
from src.procurement.procedure_models import (
    DocumentConformitySignal,
    DocumentValidity,
    M12Handoffs,
    M12Meta,
    M12Output,
    ProcedureRecognition,
    ProcessLinking,
    TracedField,
)

logger = logging.getLogger(__name__)


def _tf(
    value: Any,
    confidence: float = 0.6,
    evidence: list[str] | None = None,
) -> TracedField:
    return TracedField(value=value, confidence=confidence, evidence=evidence or [])


def _detect_framework_from_corpus(text: str) -> tuple[ProcurementFramework, float]:
    """Détection heuristique framework depuis corpus ITT/DAO.

    Returns: (framework, confidence)
    """
    text_lower = text.lower()

    dgmp_markers = [
        "direction générale des marchés publics",
        "dgmp",
        "république du mali",
        "code des marchés publics",
        "armp mali",
        "décret n°",
    ]
    dgmp_count = sum(1 for m in dgmp_markers if m in text_lower)

    sci_markers = [
        "save the children",
        "sci procurement",
        "humanitarian procurement",
        "donor compliance",
    ]
    sci_count = sum(1 for m in sci_markers if m in text_lower)

    if dgmp_count >= 2:
        return ProcurementFramework.DGMP_MALI, 0.8
    if dgmp_count == 1:
        return ProcurementFramework.DGMP_MALI, 0.6
    if sci_count >= 2:
        return ProcurementFramework.SCI, 0.8
    if sci_count == 1:
        return ProcurementFramework.SCI, 0.6
    return ProcurementFramework.UNKNOWN, 0.6


def build_pipeline_v5_minimal_m12(*, corpus_text: str) -> M12Output:
    """M12 bootstrap pour M13 — détection framework + corpus pour H1/H2/H3."""
    text = corpus_text[:500_000] if corpus_text else ""
    framework, fw_conf = _detect_framework_from_corpus(text)

    logger.info(
        "[PIPELINE-V5] M12 build — framework=%s confidence=%.1f corpus_len=%d",
        framework.value,
        fw_conf,
        len(text),
    )

    rec = ProcedureRecognition(
        framework_detected=_tf(framework, fw_conf),
        procurement_family=_tf(ProcurementFamily.GOODS),
        procurement_family_sub=_tf(ProcurementFamilySub.GENERIC),
        document_kind=_tf(DocumentKindParent.ITT),
        document_subtype=_tf(DocumentKindParent.UNKNOWN),
        is_composite=_tf(False, 1.0),
        document_layer=_tf(DocumentLayer.SOURCE_RULES),
        document_stage=_tf(DocumentStage.SOLICITATION),
        procedure_type=_tf(ProcedureType.UNKNOWN),
        procedure_reference_detected=_tf("ABSENT"),
        issuing_entity_detected=_tf("ABSENT"),
        project_name_detected=_tf("ABSENT"),
        zone_scope_detected=_tf("ABSENT"),
        submission_deadline_detected=_tf("ABSENT"),
        submission_mode_detected=_tf("ABSENT"),
        result_type_detected=_tf("ABSENT"),
        estimated_value_detected=_tf("ABSENT"),
        currency_detected=_tf("ABSENT"),
        visit_required=_tf("NOT_APPLICABLE", 1.0),
        sample_required=_tf("NOT_APPLICABLE", 1.0),
        humanitarian_context=_tf("NOT_APPLICABLE", 1.0),
        recognition_source=_tf("pipeline_v5_heuristic"),
        review_status=_tf("review_required", 0.6),
    )
    validity = DocumentValidity(
        document_validity_status=_tf("NOT_ASSESSED", 0.6, ["pipeline_v5_bootstrap"]),
    )
    conformity = DocumentConformitySignal(
        offer_composition_hint=_tf("ABSENT", 0.6),
        document_conformity_status=_tf("NOT_ASSESSED", 0.6),
        document_scope=_tf("case_level", 0.6),
        gates=[],
        eligibility_gates_extracted=[],
    )
    linking = ProcessLinking(
        process_role=_tf(ProcessRole.UNKNOWN),
        procedure_end_marker=_tf(False, 1.0, ["pipeline_v5"]),
    )
    hh: M12Handoffs = build_handoffs(
        DocumentKindParent.ITT,
        framework,
        fw_conf,
        ProcurementFamily.GOODS,
        ProcurementFamilySub.GENERIC,
        [],
        None,
        text,
    )
    meta = M12Meta(
        mode="bootstrap",
        confidence_ceiling=1.0,
        corpus_size_at_processing=len(text),
        processing_timestamp=datetime.now(UTC).isoformat(),
        pass_sequence=["pipeline_v5_heuristic"],
    )
    return M12Output(
        procedure_recognition=rec,
        document_validity=validity,
        document_conformity_signal=conformity,
        process_linking=linking,
        handoffs=hh,
        m12_meta=meta,
    )
