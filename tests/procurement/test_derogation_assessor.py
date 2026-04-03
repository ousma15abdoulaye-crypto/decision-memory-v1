"""Tests — DerogationAssessor."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from src.procurement.compliance_models_m13 import (
    DerogationType,
    NormativeReference,
    RegulatoryProcedureType,
    RegulatoryRegime,
    ThresholdTier,
)
from src.procurement.derogation_assessor import DerogationAssessor
from src.procurement.document_ontology import ProcurementFamily, ProcurementFramework
from src.procurement.procedure_models import (
    ProcedureRecognition,
    TracedField,
)
from src.procurement.regulatory_config_loader import RegulatoryConfigLoader

# ── Helpers ─────────────────────────────────────────────────────


def _tf(value: Any = None, confidence: float = 0.8) -> TracedField:
    return TracedField(value=value, confidence=confidence)


def _ref(fw: str = "sci") -> NormativeReference:
    return NormativeReference(framework=fw, description="test")


def _tier() -> ThresholdTier:
    return ThresholdTier(
        tier_name="t1",
        min_value=0.0,
        max_value=50000.0,
        currency="XOF",
        procedure_required="request_for_quotation",
        source=_ref(),
    )


def _regime(
    proc: RegulatoryProcedureType = RegulatoryProcedureType.OPEN_NATIONAL,
) -> RegulatoryRegime:
    return RegulatoryRegime(
        framework=ProcurementFramework.SCI,
        procurement_family=ProcurementFamily.GOODS,
        threshold_tier=_tier(),
        procedure_type=proc,
        confidence=0.8,
    )


def _recognition(
    humanitarian: str = "no",
    zone: str = "bamako",
) -> ProcedureRecognition:
    return ProcedureRecognition(
        framework_detected=_tf("sci"),
        procurement_family=_tf("goods"),
        procurement_family_sub=_tf("general"),
        document_kind=_tf("tender"),
        document_subtype=_tf("goods"),
        is_composite=_tf(False),
        document_layer=_tf("layer_1"),
        document_stage=_tf("solicitation"),
        procedure_type=_tf("open_national"),
        procedure_reference_detected=_tf("REF-001"),
        issuing_entity_detected=_tf("SCI Mali"),
        project_name_detected=_tf("Test Project"),
        zone_scope_detected=_tf(zone),
        submission_deadline_detected=_tf(None),
        submission_mode_detected=_tf(None),
        result_type_detected=_tf(None),
        estimated_value_detected=_tf(50000),
        currency_detected=_tf("XOF"),
        visit_required=_tf(False),
        sample_required=_tf(False),
        humanitarian_context=_tf(humanitarian),
        recognition_source=_tf("m12"),
        review_status=_tf("ok"),
    )


def _loader() -> RegulatoryConfigLoader:
    loader = MagicMock(spec=RegulatoryConfigLoader)
    loader.load_derogations.return_value = {
        "humanitarian_emergency": {
            "approval_required": "Country Director",
            "approval_authority": "CD",
            "timeline_reduction_pct": 50,
            "article": "Art. 12",
            "description": "Humanitarian emergency",
        },
        "sole_source": {
            "approval_required": "PRMP",
            "approval_authority": "PRMP",
            "article": "Art. 42",
            "description": "Sole source",
        },
        "security_context": {
            "approval_required": "SD+CD",
            "approval_authority": "SD+CD",
            "description": "Security context",
        },
    }
    return loader


# ── Tests ───────────────────────────────────────────────────────


class TestHumanitarianDerogation:
    def test_humanitarian_yes(self) -> None:
        assessor = DerogationAssessor(_loader())
        result = assessor.assess(
            _regime(), _recognition(humanitarian="yes"), _requirements_stub()
        )
        types = [d.derogation_type for d in result]
        assert DerogationType.HUMANITARIAN_EMERGENCY in types

    def test_humanitarian_no(self) -> None:
        assessor = DerogationAssessor(_loader())
        result = assessor.assess(
            _regime(), _recognition(humanitarian="no"), _requirements_stub()
        )
        types = [d.derogation_type for d in result]
        assert DerogationType.HUMANITARIAN_EMERGENCY not in types


class TestSoleSourceDerogation:
    def test_sole_source_triggered(self) -> None:
        assessor = DerogationAssessor(_loader())
        result = assessor.assess(
            _regime(RegulatoryProcedureType.SOLE_SOURCE),
            _recognition(),
            _requirements_stub(),
        )
        types = [d.derogation_type for d in result]
        assert DerogationType.SOLE_SOURCE_JUSTIFIED in types

    def test_not_sole_source(self) -> None:
        assessor = DerogationAssessor(_loader())
        result = assessor.assess(
            _regime(RegulatoryProcedureType.OPEN_NATIONAL),
            _recognition(),
            _requirements_stub(),
        )
        types = [d.derogation_type for d in result]
        assert DerogationType.SOLE_SOURCE_JUSTIFIED not in types


class TestSecurityDerogation:
    def test_gao_zone_triggers_security(self) -> None:
        assessor = DerogationAssessor(_loader())
        result = assessor.assess(
            _regime(), _recognition(zone="Gao"), _requirements_stub()
        )
        types = [d.derogation_type for d in result]
        assert DerogationType.SECURITY_CONTEXT in types

    def test_safe_zone_no_security(self) -> None:
        assessor = DerogationAssessor(_loader())
        result = assessor.assess(
            _regime(), _recognition(zone="Bamako"), _requirements_stub()
        )
        types = [d.derogation_type for d in result]
        assert DerogationType.SECURITY_CONTEXT not in types


class TestCombined:
    def test_humanitarian_plus_sole_source(self) -> None:
        assessor = DerogationAssessor(_loader())
        result = assessor.assess(
            _regime(RegulatoryProcedureType.SOLE_SOURCE),
            _recognition(humanitarian="yes"),
            _requirements_stub(),
        )
        types = [d.derogation_type for d in result]
        assert DerogationType.HUMANITARIAN_EMERGENCY in types
        assert DerogationType.SOLE_SOURCE_JUSTIFIED in types

    def test_no_derogations(self) -> None:
        assessor = DerogationAssessor(_loader())
        result = assessor.assess(_regime(), _recognition(), _requirements_stub())
        assert len(result) == 0


class TestConfidenceValues:
    def test_confidence_discretized(self) -> None:
        assessor = DerogationAssessor(_loader())
        result = assessor.assess(
            _regime(), _recognition(humanitarian="yes"), _requirements_stub()
        )
        for d in result:
            assert d.confidence in (0.6, 0.8, 1.0)


# ── Stubs ───────────────────────────────────────────────────────


def _requirements_stub():
    from src.procurement.compliance_models_m13 import (
        EvaluationRequirements,
        GuaranteeRequirements,
        MinimumBidsRequirement,
        ProcedureRequirements,
        RequiredDocumentSet,
        TimelineRequirements,
    )

    return ProcedureRequirements(
        regime=_regime(),
        required_documents=RequiredDocumentSet(),
        timeline_requirements=TimelineRequirements(),
        evaluation_requirements=EvaluationRequirements(
            evaluation_method="lowest_price"
        ),
        guarantee_requirements=GuaranteeRequirements(),
        minimum_bids=MinimumBidsRequirement(),
    )
