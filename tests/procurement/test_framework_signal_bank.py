"""Tests for src/procurement/framework_signal_bank.py — L1 framework detection."""

from __future__ import annotations

from src.procurement.document_ontology import ProcurementFramework
from src.procurement.framework_signal_bank import FrameworkSignalBank


class TestFrameworkSignalBank:
    def setup_method(self) -> None:
        self.bank = FrameworkSignalBank()

    def test_load_signals_not_empty(self) -> None:
        assert len(self.bank.signals) > 0

    def test_sci_detected_with_strong_signals(self) -> None:
        text = "Save the Children International procurement manual SCI procurement"
        decision = self.bank.detect_framework(text)
        assert decision.framework == ProcurementFramework.SCI
        assert decision.confidence >= 0.50

    def test_dgmp_detected(self) -> None:
        text = "Direction Générale des Marchés Publics code des marchés autorité contractante"
        decision = self.bank.detect_framework(text)
        assert decision.framework == ProcurementFramework.DGMP_MALI
        assert decision.confidence >= 0.50

    def test_unknown_for_empty_text(self) -> None:
        decision = self.bank.detect_framework("")
        assert decision.framework == ProcurementFramework.UNKNOWN
        assert decision.confidence <= 0.40

    def test_unknown_for_generic_text(self) -> None:
        text = "This is a simple document about cooking recipes."
        decision = self.bank.detect_framework(text)
        assert decision.framework == ProcurementFramework.UNKNOWN

    def test_mixed_when_ambiguous(self) -> None:
        text = "Save the Children SCI Direction Générale des Marchés Publics DGMP Mali"
        decision = self.bank.detect_framework(text)
        assert decision.framework in (
            ProcurementFramework.SCI,
            ProcurementFramework.DGMP_MALI,
            ProcurementFramework.MIXED,
        )

    def test_confidence_capped(self) -> None:
        text = "Save the Children " * 20
        decision = self.bank.detect_framework(text)
        assert decision.confidence <= 0.95

    def test_score_document_returns_dict(self) -> None:
        scores = self.bank.score_document("Save the Children")
        assert isinstance(scores, dict)
        assert all(isinstance(k, ProcurementFramework) for k in scores)
