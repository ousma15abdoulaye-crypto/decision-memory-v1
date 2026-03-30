"""Tests for src/procurement/mandatory_parts_engine.py — L4 mandatory parts."""

from __future__ import annotations

from src.procurement.mandatory_parts_engine import MandatoryPartsEngine


class TestMandatoryPartsEngine:
    def setup_method(self) -> None:
        self.engine = MandatoryPartsEngine()

    def test_known_types_loaded(self) -> None:
        assert "tdr" in self.engine.known_types
        assert "dao" in self.engine.known_types
        assert "rfq" in self.engine.known_types

    def test_tdr_detects_objective(self) -> None:
        text = "Objectif de la mission: réaliser une évaluation. Livrables attendus: rapport final."
        results, optional, na = self.engine.detect_parts(text, "tdr")
        detected = [r for r in results if r.detection_level != "not_detected"]
        assert len(detected) >= 1

    def test_tdr_returns_parts(self) -> None:
        text = "Objectif de la mission. Périmètre. Livrables. Profil du consultant. Modalités de soumission."
        results, optional, na = self.engine.detect_parts(text, "tdr")
        assert len(results) > 0

    def test_unknown_type_returns_empty(self) -> None:
        results, optional, na = self.engine.detect_parts("some text", "nonexistent")
        assert results == []
        assert optional == []
        assert na == []

    def test_get_rules(self) -> None:
        rules = self.engine.get_rules("tdr")
        assert rules is not None
        assert rules.document_kind == "tdr"
        assert len(rules.mandatory) > 0

    def test_detection_levels(self) -> None:
        text = "OBJECTIF de la mission\n" * 3
        results, _, _ = self.engine.detect_parts(text, "tdr")
        for r in results:
            assert r.detection_level in (
                "level_1_heading",
                "level_2_keyword",
                "level_3_llm",
                "not_detected",
            )
            assert 0.0 <= r.confidence <= 1.0
