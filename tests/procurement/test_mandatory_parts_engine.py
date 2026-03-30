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


class TestSlidingWindow:
    """Verify that level_2 keyword detection uses a sliding window."""

    def test_window_limits_scope(self) -> None:
        engine = MandatoryPartsEngine()
        keywords = ["budget", "montant", "devise"]
        hits_narrow = engine._sliding_window_keyword_hits(
            "budget. something. something. something. montant. something. devise",
            keywords,
            window_size=2,
        )
        hits_full = engine._sliding_window_keyword_hits(
            "budget. something. something. something. montant. something. devise",
            keywords,
            window_size=100,
        )
        assert hits_full == 3
        assert hits_narrow < hits_full

    def test_window_zero_returns_global(self) -> None:
        engine = MandatoryPartsEngine()
        result = engine._sliding_window_keyword_hits("a. b. c", ["a", "c"], 0)
        assert result == 2

    def test_empty_text(self) -> None:
        engine = MandatoryPartsEngine()
        assert engine._sliding_window_keyword_hits("", ["x"], 5) == 0


class TestCustomRules:
    """Verify that previously-placeholder custom rules now fire correctly."""

    def test_offer_technical_corps_detected(self) -> None:
        text = "la méthodologie proposée inclut un organigramme détaillé"
        assert MandatoryPartsEngine._run_custom_rule(
            text, "offer_technical_corps_detected"
        )

    def test_offer_financial_structure_detected(self) -> None:
        text = "bordereau des prix unitaires et montant total TTC"
        assert MandatoryPartsEngine._run_custom_rule(
            text, "offer_financial_structure_detected"
        )

    def test_detect_entity_with_address(self) -> None:
        text = "Société ABC, adresse: BP 123, Bamako"
        assert MandatoryPartsEngine._run_custom_rule(text, "detect_entity_with_address")

    def test_detect_entity_with_address_no_address(self) -> None:
        text = "Société ABC fournit des services"
        assert not MandatoryPartsEngine._run_custom_rule(
            text, "detect_entity_with_address"
        )

    def test_detect_two_distinct_named_entities(self) -> None:
        text = "entreprise alpha services et entreprise beta construction participent"
        assert MandatoryPartsEngine._run_custom_rule(
            text, "detect_two_distinct_named_entities"
        )

    def test_detect_numeric_table(self) -> None:
        text = "|item|qty|price|\n|A|100|5000|\n|B|200|10000|\n|C|50|3000|"
        assert MandatoryPartsEngine._run_custom_rule(text, "detect_numeric_table")

    def test_detect_table_headers_price(self) -> None:
        text = "description des articles | quantite | prix unitaire | montant total"
        assert MandatoryPartsEngine._run_custom_rule(text, "detect_table_headers_price")

    def test_word_count_gte_500(self) -> None:
        text = " ".join(["mot"] * 600)
        assert MandatoryPartsEngine._run_custom_rule(text, "word_count_gte_500")

    def test_word_count_gte_500_short(self) -> None:
        assert not MandatoryPartsEngine._run_custom_rule("court", "word_count_gte_500")

    def test_detect_legal_form(self) -> None:
        assert MandatoryPartsEngine._run_custom_rule(
            "forme juridique SARL", "detect_legal_form"
        )

    def test_detect_currency_and_amount(self) -> None:
        text = "montant estimé 15.000.000 FCFA"
        assert MandatoryPartsEngine._run_custom_rule(text, "detect_currency_and_amount")

    def test_detect_signature_blocks(self) -> None:
        assert MandatoryPartsEngine._run_custom_rule(
            "lu et signé", "detect_signature_blocks"
        )

    def test_detect_reference_number(self) -> None:
        assert MandatoryPartsEngine._run_custom_rule(
            "n° ABC-2024/001", "detect_reference_number"
        )

    def test_detect_hierarchical_numbering(self) -> None:
        assert MandatoryPartsEngine._run_custom_rule(
            "section 1.2.3", "detect_hierarchical_numbering"
        )

    def test_detect_unit_column(self) -> None:
        assert MandatoryPartsEngine._run_custom_rule(
            "m2 et kg requis", "detect_unit_column"
        )

    def test_detect_numeric_column_pu(self) -> None:
        assert MandatoryPartsEngine._run_custom_rule(
            "prix unitaire en FCFA", "detect_numeric_column_pu"
        )

    def test_unknown_rule_returns_false(self) -> None:
        assert not MandatoryPartsEngine._run_custom_rule("text", "nonexistent_rule")
