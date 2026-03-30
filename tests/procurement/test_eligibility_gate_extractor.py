"""Tests for src/procurement/eligibility_gate_extractor.py — L6 sub."""

from __future__ import annotations

from src.procurement.eligibility_gate_extractor import extract_eligibility_gates


class TestEligibilityGateExtractor:
    def test_empty_text_returns_empty(self) -> None:
        assert extract_eligibility_gates("") == []

    def test_nif_detected(self) -> None:
        text = "Le soumissionnaire devra fournir un NIF valide."
        gates = extract_eligibility_gates(text)
        names = [g.gate_name for g in gates]
        assert "nif_required" in names

    def test_rccm_detected(self) -> None:
        text = "Attestation du Registre du Commerce (RCCM) en cours de validité."
        gates = extract_eligibility_gates(text)
        names = [g.gate_name for g in gates]
        assert "rccm_required" in names

    def test_sci_conditions_detected(self) -> None:
        text = "Les conditions générales d'achat de Save the Children doivent être signées."
        gates = extract_eligibility_gates(text)
        names = [g.gate_name for g in gates]
        assert "sci_conditions_signed" in names

    def test_multiple_gates(self) -> None:
        text = (
            "Pièces requises: NIF, RCCM, RIB, quitus fiscal. "
            "Visite de site obligatoire. Caution de soumission requise."
        )
        gates = extract_eligibility_gates(text)
        assert len(gates) >= 4

    def test_confidence_range(self) -> None:
        text = "NIF requis"
        gates = extract_eligibility_gates(text)
        for g in gates:
            assert 0.0 <= g.confidence <= 1.0
