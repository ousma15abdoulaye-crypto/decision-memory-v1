"""Tests for src/procurement/handoff_builder.py — H1/H2/H3 handoffs."""

from __future__ import annotations

from src.procurement.document_ontology import (
    DocumentKindParent,
    ProcurementFamily,
    ProcurementFamilySub,
    ProcurementFramework,
)
from src.procurement.handoff_builder import build_handoffs


class TestBuildHandoffs:
    def test_source_rules_gets_h1_h2(self) -> None:
        handoffs = build_handoffs(
            document_kind=DocumentKindParent.TDR,
            framework=ProcurementFramework.SCI,
            framework_confidence=0.80,
            family=ProcurementFamily.CONSULTANCY,
            family_sub=ProcurementFamilySub.CONSULTANCY_EVALUATION,
            gates=[],
            scoring=None,
            text="Save the Children conditions générales d'achat TDR consultance",
        )
        assert handoffs.regulatory_profile_skeleton is not None
        assert handoffs.atomic_capability_skeleton is not None

    def test_offer_does_not_get_h1_h2(self) -> None:
        handoffs = build_handoffs(
            document_kind=DocumentKindParent.OFFER_TECHNICAL,
            framework=ProcurementFramework.SCI,
            framework_confidence=0.80,
            family=ProcurementFamily.GOODS,
            family_sub=ProcurementFamilySub.GENERIC,
            gates=[],
            scoring=None,
            text="Offre technique fournisseur",
        )
        assert handoffs.regulatory_profile_skeleton is None
        assert handoffs.atomic_capability_skeleton is None

    def test_h3_market_signal_with_prices(self) -> None:
        handoffs = build_handoffs(
            document_kind=DocumentKindParent.RFQ,
            framework=ProcurementFramework.SCI,
            framework_confidence=0.80,
            family=ProcurementFamily.GOODS,
            family_sub=ProcurementFamilySub.GENERIC,
            gates=[],
            scoring=None,
            text="Prix: 5 000 000 FCFA pour ciment et fer à béton Bamako",
        )
        assert handoffs.market_context_signal is not None
        assert handoffs.market_context_signal.prices_detected is True

    def test_h1_sci_signals(self) -> None:
        handoffs = build_handoffs(
            document_kind=DocumentKindParent.DAO,
            framework=ProcurementFramework.SCI,
            framework_confidence=0.85,
            family=ProcurementFamily.WORKS,
            family_sub=ProcurementFamilySub.CONSTRUCTION,
            gates=[],
            scoring=None,
            text="Conditions générales d'achat IAPG non-sanctions clause durabilité",
        )
        h1 = handoffs.regulatory_profile_skeleton
        assert h1 is not None
        assert h1.sci_conditions_referenced is True
        assert h1.sci_iapg_referenced is True

    def test_h2_consultancy_active_sections(self) -> None:
        handoffs = build_handoffs(
            document_kind=DocumentKindParent.TDR,
            framework=ProcurementFramework.SCI,
            framework_confidence=0.80,
            family=ProcurementFamily.CONSULTANCY,
            family_sub=ProcurementFamilySub.GENERIC,
            gates=[],
            scoring=None,
            text="TDR consultance",
        )
        h2 = handoffs.atomic_capability_skeleton
        assert h2 is not None
        assert "methodology" in h2.active_capability_sections
        assert "warehouse_capacity" not in h2.active_capability_sections
