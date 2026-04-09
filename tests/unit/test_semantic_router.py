"""Tests Semantic Router — Canon V5.1.0 Locking test 14.

INV-A03 : routing sémantique, pas regex.
Vérifie la classification des 5 IntentClass et les seuils.
"""

from __future__ import annotations

import asyncio

from src.agent.semantic_router import (
    INTENT_EXAMPLES,
    IntentClass,
    IntentResult,
    _centroid_cache,
    classify_intent,
    reset_centroid_cache,
    warm_centroids,
)


def _run(coro):
    return asyncio.run(coro)


class TestIntentClassEnum:
    def test_five_classes(self):
        assert len(IntentClass) == 5

    def test_values(self):
        expected = {
            "market_query",
            "workspace_status",
            "process_info",
            "recommendation",
            "out_of_scope",
        }
        assert {c.value for c in IntentClass} == expected


class TestClassifyIntent:
    def setup_method(self):
        reset_centroid_cache()

    def test_returns_intent_result(self):
        result = _run(classify_intent("prix du ciment"))
        assert isinstance(result, IntentResult)
        assert isinstance(result.intent_class, IntentClass)
        assert 0.0 <= result.confidence <= 1.0

    def test_market_query_detected(self):
        result = _run(classify_intent("Quel est le prix du ciment à Mopti ?"))
        assert result.intent_class in (
            IntentClass.MARKET_QUERY,
            IntentClass.OUT_OF_SCOPE,
        )

    def test_recommendation_query_flagged(self):
        result = _run(
            classify_intent("Quel fournisseur est le meilleur pour ce marché ?")
        )
        assert result.intent_class in (
            IntentClass.RECOMMENDATION,
            IntentClass.OUT_OF_SCOPE,
        )

    def test_out_of_scope_for_unrelated(self):
        result = _run(classify_intent("Quelle est la météo à Paris ?"))
        assert result.confidence < 1.0


class TestWarmCentroids:
    """Tests warm_centroids() — pré-calcul au démarrage (BUG-P1-01)."""

    def setup_method(self):
        reset_centroid_cache()

    def test_warm_centroids_fills_cache(self):
        """warm_centroids() remplit le cache pour les classes dans INTENT_EXAMPLES (pas OUT_OF_SCOPE)."""
        assert len(_centroid_cache) == 0
        _run(warm_centroids())
        assert set(_centroid_cache.keys()) == set(INTENT_EXAMPLES.keys())
        assert IntentClass.OUT_OF_SCOPE not in _centroid_cache

    def test_warm_centroids_is_idempotent(self):
        """Appeler warm_centroids() deux fois ne doit pas recalculer (idempotent)."""
        _run(warm_centroids())
        first_ids = {k: id(v) for k, v in _centroid_cache.items()}
        _run(warm_centroids())
        # Le cache ne doit pas changer (mêmes objets ndarray)
        assert {k: id(v) for k, v in _centroid_cache.items()} == first_ids

    def test_warm_centroids_allows_classify(self):
        """Après warm_centroids(), classify_intent ne doit pas recalculer les centroïdes."""
        _run(warm_centroids())
        cache_size_before = len(_centroid_cache)
        result = _run(classify_intent("prix du ciment à Bamako"))
        assert isinstance(result, IntentResult)
        # Le cache ne doit pas avoir grossi
        assert len(_centroid_cache) == cache_size_before
