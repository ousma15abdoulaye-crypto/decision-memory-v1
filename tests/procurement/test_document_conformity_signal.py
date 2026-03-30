"""Tests for src/procurement/document_conformity_signal.py — L6 conformity."""

from __future__ import annotations

from src.procurement.document_conformity_signal import compute_conformity_signal
from src.procurement.document_ontology import DocumentKindParent
from src.procurement.procedure_models import (
    DocumentValidity,
    TracedField,
)


def _make_validity(status: str, coverage: float) -> DocumentValidity:
    return DocumentValidity(
        document_validity_status=TracedField(
            value=status, confidence=0.80, evidence=["test"]
        ),
        mandatory_detected_count=int(coverage * 5),
        mandatory_total_count=5,
        mandatory_coverage=coverage,
    )


class TestConformitySignal:
    def test_valid_tdr_is_conforme(self) -> None:
        validity = _make_validity("valid", 1.0)
        signal = compute_conformity_signal(DocumentKindParent.TDR, "no", validity)
        assert signal.document_conformity_status.value == "conforme"

    def test_invalid_offer_is_non_conforme(self) -> None:
        validity = _make_validity("invalid", 0.0)
        signal = compute_conformity_signal(
            DocumentKindParent.OFFER_TECHNICAL, "no", validity
        )
        assert signal.document_conformity_status.value == "non_conforme"

    def test_not_assessable_is_non_statuable(self) -> None:
        validity = _make_validity("not_assessable", 0.0)
        signal = compute_conformity_signal(
            DocumentKindParent.UNKNOWN, "unknown", validity
        )
        assert signal.document_conformity_status.value == "non_statuable"

    def test_offer_composition_hint_not_offer(self) -> None:
        validity = _make_validity("valid", 1.0)
        signal = compute_conformity_signal(DocumentKindParent.TDR, "no", validity)
        assert signal.offer_composition_hint.value == "not_an_offer"

    def test_offer_composition_technical_only(self) -> None:
        validity = _make_validity("valid", 1.0)
        signal = compute_conformity_signal(
            DocumentKindParent.OFFER_TECHNICAL, "no", validity
        )
        assert signal.offer_composition_hint.value == "technical_only"

    def test_combined_offer_standalone(self) -> None:
        validity = _make_validity("valid", 1.0)
        signal = compute_conformity_signal(
            DocumentKindParent.OFFER_COMBINED, "no", validity
        )
        assert signal.offer_composition_hint.value == "standalone_offer"

    def test_document_scope_always_document_only(self) -> None:
        validity = _make_validity("valid", 1.0)
        signal = compute_conformity_signal(DocumentKindParent.TDR, "no", validity)
        assert signal.document_scope.value == "document_only"
