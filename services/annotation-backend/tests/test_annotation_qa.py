"""Tests annotation_qa — parse_loose_money_float, réconciliation."""

from __future__ import annotations

from annotation_qa import (
    evidence_substring_violations,
    parse_loose_money_float,
    should_run_financial_reconciliation,
)


def test_parse_loose_money_float_nested_value_dict():
    """Évite unhashable dict dans VALUE_SKIP ; déplie value imbriquée."""
    assert parse_loose_money_float({"value": 1_000_000}) == 1_000_000.0
    assert parse_loose_money_float({"value": {"value": "500"}}) == 500.0
    assert parse_loose_money_float({"value": None}) is None


def test_should_run_financial_reconciliation_total_value_dict():
    """Ne lève pas si total_price.value est un dict avec montant scalaire imbriqué."""
    ann = {
        "couche_1_routing": {
            "document_role": "source_rules",
            "taxonomy_core": "dao_construction_goods",
        },
        "couche_4_atomic": {
            "financier": {
                "total_price": {
                    "value": {"value": "1000"},
                    "confidence": 0.8,
                    "evidence": "p.1",
                },
                "line_items": [],
            }
        },
    }
    assert should_run_financial_reconciliation(ann) is True


def test_evidence_substring_fieldvalue_list_value_no_typeerror():
    """Valeur FieldValue en liste : pas de ``val in frozenset`` (unhashable)."""
    ann = {
        "couche_2_core": {
            "lot_scope": {
                "value": ["lot-a"],
                "confidence": 0.8,
                "evidence": "lot a dans le texte source",
            }
        }
    }
    src = "Lot A dans le texte source"
    v = evidence_substring_violations(ann, src)
    assert isinstance(v, list)
