"""
Tests DETTE-8 — imc_signals.py
RÈGLE-17 : tests prouvant les invariants métier.
RÈGLE-07 : assertions explicites — zéro '...'.
RÈGLE-09 : zéro recommendation / winner / rank dans les résultats.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────
# FIXTURE TRANSACTIONNELLE
# ─────────────────────────────────────────────────────────


@pytest.fixture
def db_tx(db_conn):
    """
    Connexion transactionnelle isolée.
    autocommit=False + rollback teardown.
    Zéro pollution DB entre les runs (E-24).
    """
    db_conn.autocommit = False
    yield db_conn
    db_conn.rollback()
    db_conn.autocommit = True


# ─────────────────────────────────────────────────────────
# CLASSIFY_IMC_SIGNAL — unitaires purs
# ─────────────────────────────────────────────────────────


def test_classify_imc_signal_critical():
    """YOY > 15% → CRITICAL."""
    from src.couche_b.imc_signals import classify_imc_signal

    result = classify_imc_signal(variation_mom=2.0, variation_yoy=16.0)
    assert result == "CRITICAL"


def test_classify_imc_signal_strong():
    """MOM > 8% → STRONG."""
    from src.couche_b.imc_signals import classify_imc_signal

    result = classify_imc_signal(variation_mom=9.5, variation_yoy=5.0)
    assert result == "STRONG"


def test_classify_imc_signal_watch():
    """MOM > 3% et YOY ≤ 15% → WATCH."""
    from src.couche_b.imc_signals import classify_imc_signal

    result = classify_imc_signal(variation_mom=4.0, variation_yoy=10.0)
    assert result == "WATCH"


def test_classify_imc_signal_stable():
    """MOM ≤ 3% → STABLE."""
    from src.couche_b.imc_signals import classify_imc_signal

    result = classify_imc_signal(variation_mom=1.5, variation_yoy=2.0)
    assert result == "STABLE"


def test_classify_imc_signal_none_values():
    """mom=None et yoy=None → UNKNOWN."""
    from src.couche_b.imc_signals import classify_imc_signal

    result = classify_imc_signal(variation_mom=None, variation_yoy=None)
    assert result == "UNKNOWN"


def test_classify_imc_signal_priority_critical_over_strong():
    """CRITICAL prioritaire sur STRONG."""
    from src.couche_b.imc_signals import classify_imc_signal

    result = classify_imc_signal(variation_mom=9.0, variation_yoy=20.0)
    assert result == "CRITICAL"


# ─────────────────────────────────────────────────────────
# COMPUTE_IMC_ENRICHMENT — avec mock connexion
# ─────────────────────────────────────────────────────────


def test_compute_imc_enrichment_no_mapping():
    """
    Aucun mapping IMC → imc_revision_applied=False + error=no_imc_mapping.
    """
    from src.couche_b.imc_signals import compute_imc_enrichment

    with patch(
        "src.couche_b.imc_signals.get_latest_imc_for_item",
        return_value=None,
    ):
        result = compute_imc_enrichment(
            conn=MagicMock(),
            signal_id="sig-001",
            item_id="item-001",
            price_avg=10000.0,
        )

    assert result["imc_revision_applied"] is False
    assert result["error"] == "no_imc_mapping"
    assert result["revised_price_avg"] is None


def test_compute_imc_enrichment_no_baseline():
    """
    Mapping IMC présent mais pas de baseline → error=no_baseline.
    Signal classifié quand même avec variation_mom/yoy.
    """
    from src.couche_b.imc_signals import compute_imc_enrichment

    fake_latest = {
        "index_value": 112.0,
        "year": 2025,
        "month": 6,
        "category_raw": "LIANTS HYDRAULIQUES",
        "variation_mom": 5.0,
        "variation_yoy": 12.0,
        "mapping_confidence": 1.0,
        "mapping_method": "manual",
    }

    with (
        patch(
            "src.couche_b.imc_signals.get_latest_imc_for_item",
            return_value=fake_latest,
        ),
        patch(
            "src.couche_b.imc_signals.get_baseline_imc_for_item",
            return_value=None,
        ),
    ):
        result = compute_imc_enrichment(
            conn=MagicMock(),
            signal_id="sig-002",
            item_id="item-001",
            price_avg=10000.0,
        )

    assert result["imc_revision_applied"] is False
    assert result["error"] == "no_baseline"
    assert result["imc_signal_class"] == "WATCH"


def test_compute_imc_enrichment_nominal():
    """
    Mapping + baseline → révision appliquée.
    Vérifier factor = IMC_t1 / IMC_t0.
    """
    from src.couche_b.imc_signals import compute_imc_enrichment

    fake_latest = {
        "index_value": 112.0,
        "year": 2025,
        "month": 6,
        "category_raw": "LIANTS HYDRAULIQUES",
        "variation_mom": 4.0,  # MOM > 3% → WATCH
        "variation_yoy": 12.0,
        "mapping_confidence": 1.0,
        "mapping_method": "manual",
    }
    fake_baseline = {
        "index_value": 100.0,
        "year": 2023,
        "month": 1,
        "category_raw": "LIANTS HYDRAULIQUES",
    }

    with (
        patch(
            "src.couche_b.imc_signals.get_latest_imc_for_item",
            return_value=fake_latest,
        ),
        patch(
            "src.couche_b.imc_signals.get_baseline_imc_for_item",
            return_value=fake_baseline,
        ),
    ):
        result = compute_imc_enrichment(
            conn=MagicMock(),
            signal_id="sig-003",
            item_id="item-001",
            price_avg=10000.0,
        )

    assert result["imc_revision_applied"] is True
    assert result["error"] is None
    assert result["imc_revision_factor"] == pytest.approx(1.12, rel=1e-4)
    assert result["revised_price_avg"] == pytest.approx(11200.0, rel=1e-4)
    assert result["imc_signal_class"] == "WATCH"


def test_compute_imc_enrichment_no_price_avg():
    """
    price_avg=None → révision non appliquée (pas de prix à réviser).
    """
    from src.couche_b.imc_signals import compute_imc_enrichment

    fake_latest = {
        "index_value": 112.0,
        "year": 2025,
        "month": 6,
        "category_raw": "AGREGATS",
        "variation_mom": 2.0,
        "variation_yoy": 5.0,
        "mapping_confidence": 0.8,
        "mapping_method": "manual",
    }
    fake_baseline = {
        "index_value": 100.0,
        "year": 2023,
        "month": 1,
        "category_raw": "AGREGATS",
    }

    with (
        patch(
            "src.couche_b.imc_signals.get_latest_imc_for_item",
            return_value=fake_latest,
        ),
        patch(
            "src.couche_b.imc_signals.get_baseline_imc_for_item",
            return_value=fake_baseline,
        ),
    ):
        result = compute_imc_enrichment(
            conn=MagicMock(),
            signal_id="sig-004",
            item_id="item-001",
            price_avg=None,
        )

    assert result["imc_revision_applied"] is False
    assert result["error"] == "no_price_avg"


# ─────────────────────────────────────────────────────────
# RÈGLE-09 — ZÉRO recommendation / winner / rank
# ─────────────────────────────────────────────────────────


def test_no_recommendation_in_enrichment_result():
    """
    RÈGLE-09 : le résultat d'enrichissement ne contient
    jamais recommendation / winner / rank / best_offer.
    """
    from src.couche_b.imc_signals import compute_imc_enrichment

    with patch(
        "src.couche_b.imc_signals.get_latest_imc_for_item",
        return_value=None,
    ):
        result = compute_imc_enrichment(
            conn=MagicMock(),
            signal_id="sig-005",
            item_id="item-001",
            price_avg=10000.0,
        )

    forbidden = {"recommendation", "winner", "rank", "best_offer"}
    result_keys = set(result.keys())
    assert not forbidden.intersection(result_keys), (
        f"RÈGLE-09 violée — champs interdits : "
        f"{forbidden.intersection(result_keys)}"
    )


def test_no_recommendation_in_batch_metrics():
    """
    RÈGLE-09 : les métriques du batch ne contiennent
    jamais recommendation / winner / rank / best_offer.
    """
    from src.couche_b.imc_signals import run_imc_enrichment_batch

    with patch(
        "src.couche_b.imc_signals.get_signals_pending_imc",
        return_value=[],
    ):
        metrics = run_imc_enrichment_batch(conn=MagicMock())

    forbidden = {"recommendation", "winner", "rank", "best_offer"}
    assert not forbidden.intersection(
        set(metrics.keys())
    ), "RÈGLE-09 violée dans batch metrics"


# ─────────────────────────────────────────────────────────
# BATCH — comportement avec liste vide
# ─────────────────────────────────────────────────────────


def test_batch_empty_signals():
    """Batch avec 0 signaux → métriques cohérentes."""
    from src.couche_b.imc_signals import run_imc_enrichment_batch

    with patch(
        "src.couche_b.imc_signals.get_signals_pending_imc",
        return_value=[],
    ):
        metrics = run_imc_enrichment_batch(conn=MagicMock())

    assert metrics["total_processed"] == 0
    assert metrics["total_enriched"] == 0
    assert metrics["total_skipped"] == 0
    assert metrics["errors"] == []
    assert metrics["formula_version"] == "imc_1.0"


# ─────────────────────────────────────────────────────────
# COVERAGE STATS — structure
# ─────────────────────────────────────────────────────────


def test_imc_coverage_stats_structure(db_conn):
    """
    get_imc_coverage_stats retourne les champs attendus.
    Test sur DB réelle — lecture seule.
    """
    from src.couche_b.imc_signals import get_imc_coverage_stats

    stats = get_imc_coverage_stats(db_conn)

    required_keys = {
        "total_signals",
        "enriched",
        "pending",
        "enrichment_rate",
        "avg_revision_factor",
        "formula_version",
    }
    assert required_keys.issubset(
        set(stats.keys())
    ), f"Clés manquantes : {required_keys - set(stats.keys())}"
    assert stats["formula_version"] == "imc_1.0"
    assert 0.0 <= stats["enrichment_rate"] <= 100.0
    assert stats["total_signals"] >= 0


# ─────────────────────────────────────────────────────────
# MARKET_SIGNALS_V2 — colonnes 046b présentes
# ─────────────────────────────────────────────────────────


def test_market_signals_v2_has_imc_columns(db_conn):
    """
    market_signals_v2 possède les colonnes IMC ajoutées par 046b.
    Invariant probe ÉTAPE 0.
    """
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'market_signals_v2';
            """)
        cols = {row["column_name"] for row in cur.fetchall()}

    assert (
        "imc_revision_applied" in cols
    ), "imc_revision_applied absent — 046b non appliqué"
    assert (
        "imc_revision_factor" in cols
    ), "imc_revision_factor absent — 046b non appliqué"
    assert "imc_revision_at" in cols, "imc_revision_at absent — 046b non appliqué"
