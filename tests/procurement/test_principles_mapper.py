"""Tests — PrinciplesMapper (9 principles, SUSTAINABILITY present)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.procurement.compliance_models_m13 import (
    EvaluationRequirements,
    GuaranteeRequirements,
    MinimumBidsRequirement,
    NormativeReference,
    ProcedureRequirements,
    ProcurementPrinciple,
    RegulatoryProcedureType,
    RegulatoryRegime,
    RequiredDocumentSet,
    ThresholdTier,
    TimelineRequirements,
)
from src.procurement.document_ontology import ProcurementFamily, ProcurementFramework
from src.procurement.principles_mapper import PrinciplesMapper
from src.procurement.regulatory_config_loader import RegulatoryConfigLoader

# ── Fixtures ────────────────────────────────────────────────────


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


def _regime(family: ProcurementFamily = ProcurementFamily.GOODS) -> RegulatoryRegime:
    return RegulatoryRegime(
        framework=ProcurementFramework.SCI,
        procurement_family=family,
        threshold_tier=_tier(),
        procedure_type=RegulatoryProcedureType.OPEN_NATIONAL,
        confidence=0.8,
    )


def _requirements() -> ProcedureRequirements:
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


def _loader(pm: dict | None = None) -> RegulatoryConfigLoader:
    loader = MagicMock(spec=RegulatoryConfigLoader)
    bundle = {
        "principles_mapping": {
            "principle_mappings": pm or {},
        },
    }
    loader.load_framework_bundle.return_value = bundle
    return loader


def _full_pm() -> dict:
    """Minimal principles mapping with all 9 principles present."""
    base: dict[str, dict] = {}
    for p in ProcurementPrinciple:
        base[p.value] = {
            "coverage": "partial",
            "rules_implementing": [
                {
                    "rule": f"rule_{p.value}",
                    "description": f"Implements {p.value}",
                    "contribution": "medium",
                }
            ],
        }
    base["sustainability"]["coverage"] = "full"
    base["sustainability"]["gap"] = None
    base["fit_for_purpose"]["durability_coverage"] = "partial"
    base["fit_for_purpose"]["durability_indicators"] = [
        {
            "rule": "warranty_clause",
            "description": "Warranty",
            "contribution": "strong",
            "active_for_families": ["goods", "works"],
        }
    ]
    return base


# ── Tests ───────────────────────────────────────────────────────


class TestPrinciplesCoverage:
    def test_nine_principles_always(self) -> None:
        mapper = PrinciplesMapper(_loader(_full_pm()))
        result = mapper.map_principles(_regime(), _requirements())
        assert len(result.principles) == 9

    def test_sustainability_present(self) -> None:
        mapper = PrinciplesMapper(_loader(_full_pm()))
        result = mapper.map_principles(_regime(), _requirements())
        names = {p.principle for p in result.principles}
        assert ProcurementPrinciple.SUSTAINABILITY in names

    def test_empty_pm_defaults_to_not_assessable(self) -> None:
        mapper = PrinciplesMapper(_loader({}))
        result = mapper.map_principles(_regime(), _requirements())
        assert len(result.principles) == 9
        for p in result.principles:
            assert p.status in (
                "fully_addressed",
                "partially_addressed",
                "minimally_addressed",
                "not_addressed",
                "not_assessable",
            )


class TestCoverageMapping:
    def test_full_coverage(self) -> None:
        pm = _full_pm()
        pm["competition"]["coverage"] = "full"
        mapper = PrinciplesMapper(_loader(pm))
        result = mapper.map_principles(_regime(), _requirements())
        comp = next(
            p
            for p in result.principles
            if p.principle == ProcurementPrinciple.COMPETITION
        )
        assert comp.status == "fully_addressed"

    def test_partial_coverage(self) -> None:
        pm = _full_pm()
        pm["transparency"]["coverage"] = "partial"
        mapper = PrinciplesMapper(_loader(pm))
        result = mapper.map_principles(_regime(), _requirements())
        tr = next(
            p
            for p in result.principles
            if p.principle == ProcurementPrinciple.TRANSPARENCY
        )
        assert tr.status == "partially_addressed"

    def test_none_coverage(self) -> None:
        pm = _full_pm()
        pm["economy"]["coverage"] = "none"
        mapper = PrinciplesMapper(_loader(pm))
        result = mapper.map_principles(_regime(), _requirements())
        eco = next(
            p for p in result.principles if p.principle == ProcurementPrinciple.ECONOMY
        )
        assert eco.status == "not_addressed"


class TestDurability:
    def test_durability_for_goods(self) -> None:
        pm = _full_pm()
        mapper = PrinciplesMapper(_loader(pm))
        result = mapper.map_principles(
            _regime(ProcurementFamily.GOODS), _requirements()
        )
        ffp = next(
            p
            for p in result.principles
            if p.principle == ProcurementPrinciple.FIT_FOR_PURPOSE
        )
        assert ffp.durability_assessment is not None
        assert ffp.durability_assessment.applicable is True

    def test_durability_not_applicable_services(self) -> None:
        pm = _full_pm()
        mapper = PrinciplesMapper(_loader(pm))
        result = mapper.map_principles(
            _regime(ProcurementFamily.SERVICES), _requirements()
        )
        ffp = next(
            p
            for p in result.principles
            if p.principle == ProcurementPrinciple.FIT_FOR_PURPOSE
        )
        assert ffp.durability_assessment is not None
        assert ffp.durability_assessment.applicable is False


class TestSummaryLines:
    def test_executive_summary(self) -> None:
        mapper = PrinciplesMapper(_loader(_full_pm()))
        result = mapper.map_principles(_regime(), _requirements())
        assert len(result.executive_summary_lines) == 9

    def test_sustainability_highlight(self) -> None:
        mapper = PrinciplesMapper(_loader(_full_pm()))
        result = mapper.map_principles(_regime(), _requirements())
        assert result.sustainability_highlight != ""
