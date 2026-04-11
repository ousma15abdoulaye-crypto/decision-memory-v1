"""Minimal M12 payloads for M13 / Pass 2A tests."""

from __future__ import annotations

from datetime import UTC, datetime

from src.procurement.document_ontology import (
    DocumentKindParent,
    LinkNature,
    ProcessRole,
    ProcurementFramework,
)
from src.procurement.procedure_models import (
    DocumentConformitySignal,
    DocumentValidity,
    LinkHint,
    M12Handoffs,
    M12Meta,
    M12Output,
    ProcedureRecognition,
    ProcessLinking,
    RegulatoryProfileSkeleton,
    TracedField,
)


def _tf(value: object, confidence: float = 0.9) -> TracedField:
    return TracedField(value=value, confidence=confidence, evidence=[])


def minimal_procedure_recognition_sci_goods(
    *, estimated_value: float | None = 100_000.0, currency: str = "USD"
) -> ProcedureRecognition:
    return ProcedureRecognition(
        framework_detected=_tf("sci"),
        procurement_family=_tf("goods"),
        procurement_family_sub=_tf("generic"),
        document_kind=_tf(DocumentKindParent.TDR.value),
        document_subtype=_tf("generic"),
        secondary_document_kinds=[],
        is_composite=_tf(False),
        document_layer=_tf("source_rules_layer"),
        document_stage=_tf("solicitation"),
        procedure_type=_tf("open_competitive"),
        procedure_reference_detected=_tf("SCI-REF-1"),
        issuing_entity_detected=_tf("SCI"),
        project_name_detected=_tf("Test project"),
        zone_scope_detected=_tf(["ML"]),
        submission_deadline_detected=_tf(None, 0.0),
        submission_mode_detected=_tf("email"),
        result_type_detected=_tf("unknown"),
        estimated_value_detected=_tf(estimated_value, 0.85),
        currency_detected=_tf(currency),
        visit_required=_tf(False),
        sample_required=_tf(False),
        humanitarian_context=_tf(False),
        recognition_source=_tf("test"),
        review_status=_tf("ok"),
    )


def minimal_m12_output_with_h1(
    *,
    framework: ProcurementFramework = ProcurementFramework.SCI,
    framework_confidence: float = 0.92,
    estimated_value: float | None = 100_000.0,
) -> M12Output:
    rec = minimal_procedure_recognition_sci_goods(estimated_value=estimated_value)
    validity = DocumentValidity(
        document_validity_status=_tf("valid"),
    )
    conformity = DocumentConformitySignal(
        offer_composition_hint=_tf("single_offer"),
        document_conformity_status=_tf("conform"),
        document_scope=_tf("single"),
        gates=[],
    )
    linking = ProcessLinking(
        process_role=_tf(ProcessRole.DEFINES_NEED.value),
        procedure_end_marker=_tf(False),
        linked_parent_hint=[
            LinkHint(
                target_document_id=None,
                link_nature=LinkNature.RESPONDS_TO,
                link_level="UNRESOLVED",
                confidence=0.5,
                evidence=[],
            )
        ],
    )
    skeleton = RegulatoryProfileSkeleton(
        framework_detected=framework,
        framework_confidence=framework_confidence,
        sci_signals_detected=["procurement_manual"],
    )
    handoffs = M12Handoffs(regulatory_profile_skeleton=skeleton)

    meta = M12Meta(
        mode="bootstrap",
        confidence_ceiling=1.0,
        corpus_size_at_processing=0,
        processing_timestamp=datetime.now(UTC).isoformat(),
        pass_sequence=["1a", "1b", "1c", "1d"],
    )
    return M12Output(
        procedure_recognition=rec,
        document_validity=validity,
        document_conformity_signal=conformity,
        process_linking=linking,
        handoffs=handoffs,
        m12_meta=meta,
    )


def pass_output_dicts_from_m12(m12: M12Output) -> tuple[dict, dict, dict, dict]:
    """Serial shapes expected by build_m12_output_from_pass_outputs / Pass 2A."""
    pass_1a = {"m12_recognition": m12.procedure_recognition.model_dump(mode="json")}
    pass_1b = {"m12_validity": m12.document_validity.model_dump(mode="json")}
    pass_1c = {
        "m12_conformity": m12.document_conformity_signal.model_dump(mode="json"),
        "m12_handoffs": m12.handoffs.model_dump(mode="json"),
    }
    pass_1d = {"m12_linking": m12.process_linking.model_dump(mode="json")}
    return pass_1a, pass_1b, pass_1c, pass_1d
