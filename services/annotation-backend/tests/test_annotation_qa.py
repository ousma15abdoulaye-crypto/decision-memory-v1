"""Tests annotation_qa — parse_loose_money_float, réconciliation."""

from __future__ import annotations

from annotation_qa import (
    financial_coherence_warnings,
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


# ---------------------------------------------------------------------------
# financial_coherence_warnings — logique OR ARCH-03
# ---------------------------------------------------------------------------


def _make_ann(total: float, line_items: list[dict]) -> dict:
    """Construit une annotation minimale valide pour financial_coherence_warnings."""
    return {
        "couche_1_routing": {
            "document_role": "source_rules",
            "taxonomy_core": "dao_construction_goods",
        },
        "couche_4_atomic": {
            "financier": {
                "total_price": {"value": total, "confidence": 0.8, "evidence": "p.1"},
                "line_items": line_items,
            }
        },
    }


def test_financial_coherence_warnings_details_match_no_anomaly():
    """ARCH-03 : sum(detail)==total_price même si sum(subtotal)!=total_price → aucune anomalie."""
    ann = _make_ann(
        total=1000.0,
        line_items=[
            {"level": "detail", "line_total": 400.0},
            {"level": "detail", "line_total": 600.0},
            # sous-total de section ≠ total_price
            {"level": "subtotal", "line_total": 500.0},
        ],
    )
    assert financial_coherence_warnings(ann) == []


def test_financial_coherence_warnings_subtotals_match_no_anomaly():
    """ARCH-03 : sum(subtotal)==total_price même si sum(detail)!=total_price → aucune anomalie."""
    ann = _make_ann(
        total=1000.0,
        line_items=[
            # détails partiels (double-comptage volontaire dans les lignes détail)
            {"level": "detail", "line_total": 300.0},
            {"level": "detail", "line_total": 300.0},
            # sous-totaux de section qui couvrent exactement total_price
            {"level": "subtotal", "line_total": 600.0},
            {"level": "subtotal", "line_total": 400.0},
        ],
    )
    assert financial_coherence_warnings(ann) == []


def test_financial_coherence_warnings_neither_matches_emits_anomaly():
    """Ni sum(detail) ni sum(subtotal) ne réconcilie → anomalie avec les deux agrégats."""
    ann = _make_ann(
        total=1000.0,
        line_items=[
            {"level": "detail", "line_total": 300.0},
            {"level": "detail", "line_total": 400.0},  # sum_details=700
            {"level": "subtotal", "line_total": 800.0},  # sum_subtotals=800
        ],
    )
    result = financial_coherence_warnings(ann)
    assert len(result) == 1
    assert result[0] == "ANOMALY_total_price_1000_vs_sum_details_700_sum_subtotals_800"
