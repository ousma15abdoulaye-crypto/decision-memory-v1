"""Tests annotation_qa — parse_loose_money_float, réconciliation."""

from __future__ import annotations

from annotation_qa import parse_loose_money_float, should_run_financial_reconciliation


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
