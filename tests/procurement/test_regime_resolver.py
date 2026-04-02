"""RegimeResolver — UNKNOWN / SCI single-framework."""

from __future__ import annotations

from src.procurement.compliance_models_m13 import RegulatoryProcedureType
from src.procurement.document_ontology import ProcurementFramework
from src.procurement.regime_resolver import RegimeResolver
from src.procurement.regulatory_config_loader import RegulatoryConfigLoader
from tests.procurement.m13_test_fixtures import (
    minimal_m12_output_with_h1,
    minimal_procedure_recognition_sci_goods,
)


class TestRegimeResolver:
    def test_unknown_framework(self) -> None:
        m12 = minimal_m12_output_with_h1(framework=ProcurementFramework.UNKNOWN)
        sk = m12.handoffs.regulatory_profile_skeleton
        assert sk is not None
        r = RegimeResolver(RegulatoryConfigLoader()).resolve(
            sk, m12.procedure_recognition
        )
        assert r.framework == ProcurementFramework.UNKNOWN
        assert r.procedure_type == RegulatoryProcedureType.UNKNOWN

    def test_sci_resolves_tier(self) -> None:
        m12 = minimal_m12_output_with_h1(
            framework=ProcurementFramework.SCI, estimated_value=100_000.0
        )
        sk = m12.handoffs.regulatory_profile_skeleton
        assert sk is not None
        r = RegimeResolver(RegulatoryConfigLoader()).resolve(
            sk, m12.procedure_recognition
        )
        assert r.framework == ProcurementFramework.SCI
        assert "tier" in r.threshold_tier.tier_name.lower()

    def test_mixed_uses_other_framework_signals(self) -> None:
        rec = minimal_procedure_recognition_sci_goods()
        from src.procurement.procedure_models import RegulatoryProfileSkeleton

        sk = RegulatoryProfileSkeleton(
            framework_detected=ProcurementFramework.MIXED,
            framework_confidence=0.85,
            other_framework_signals={"sci": [], "dgmp_mali": []},
        )
        r = RegimeResolver(RegulatoryConfigLoader()).resolve(sk, rec)
        assert r.is_mixed_framework is True
        assert r.framework in (
            ProcurementFramework.SCI,
            ProcurementFramework.DGMP_MALI,
        )
