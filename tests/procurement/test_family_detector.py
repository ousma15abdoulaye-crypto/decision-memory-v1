"""Tests for src/procurement/family_detector.py — L2 family detection."""

from __future__ import annotations

from src.procurement.document_ontology import ProcurementFamily
from src.procurement.family_detector import FamilyDetector


class TestFamilyDetector:
    def setup_method(self) -> None:
        self.detector = FamilyDetector()

    def test_goods_detected(self) -> None:
        text = "Fourniture de matériel informatique équipement livraison produits"
        decision = self.detector.detect_family(text)
        assert decision.family == ProcurementFamily.GOODS

    def test_works_detected(self) -> None:
        text = (
            "Travaux de construction réhabilitation bâtiment chantier génie civil BTP"
        )
        decision = self.detector.detect_family(text)
        assert decision.family == ProcurementFamily.WORKS

    def test_consultancy_detected(self) -> None:
        text = "Consultance bureau d'études évaluation finale termes de référence audit"
        decision = self.detector.detect_family(text)
        assert decision.family == ProcurementFamily.CONSULTANCY

    def test_services_detected(self) -> None:
        text = "Prestation de service maintenance nettoyage gardiennage transport"
        decision = self.detector.detect_family(text)
        assert decision.family == ProcurementFamily.SERVICES

    def test_unknown_for_empty(self) -> None:
        decision = self.detector.detect_family("")
        assert decision.family == ProcurementFamily.UNKNOWN

    def test_confidence_range(self) -> None:
        text = "Fourniture de matériel"
        decision = self.detector.detect_family(text)
        assert 0.0 <= decision.confidence <= 1.0
