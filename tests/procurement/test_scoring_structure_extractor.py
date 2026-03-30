"""Tests for src/procurement/scoring_structure_extractor.py — L6 sub."""

from __future__ import annotations

from src.procurement.scoring_structure_extractor import extract_scoring_structure


class TestScoringStructureExtractor:
    def test_empty_text(self) -> None:
        result = extract_scoring_structure("")
        assert result.ponderation_coherence == "NOT_FOUND"
        assert result.confidence == 0.0

    def test_detects_criteria(self) -> None:
        text = (
            "Critères d'évaluation:\n"
            "- Qualité technique: 70 points\n"
            "- Prix: 30 points\n"
        )
        result = extract_scoring_structure(text)
        assert len(result.criteria) >= 1

    def test_detects_method_lowest_price(self) -> None:
        text = "L'offre retenue sera celle du moins-disant conforme."
        result = extract_scoring_structure(text)
        assert result.evaluation_method == "lowest_price"

    def test_detects_method_mieux_disant(self) -> None:
        text = "Le marché sera attribué au mieux-disant."
        result = extract_scoring_structure(text)
        assert result.evaluation_method == "mieux_disant"

    def test_detects_technical_threshold(self) -> None:
        text = "Seuil technique minimum de 70/100 requis."
        result = extract_scoring_structure(text)
        assert result.technical_threshold is not None
