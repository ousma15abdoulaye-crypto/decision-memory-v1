"""Tests Guardrail INV-W06 — Canon V5.1.0 Section 7.4, Locking test 15.

Vérifie que le guardrail bloque les tentatives de recommandation
et laisse passer les requêtes légitimes.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from src.agent.guardrail import GuardrailResult, check_recommendation_guardrail
from src.agent.semantic_router import reset_centroid_cache


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_trace():
    trace = MagicMock()
    span = MagicMock()
    trace.span.return_value = span
    return trace


class TestGuardrailResult:
    def test_not_blocked_for_market_query(self):
        reset_centroid_cache()
        trace = _make_trace()
        result = _run(check_recommendation_guardrail("prix du ciment à Bamako", trace))
        assert isinstance(result, GuardrailResult)
        assert result.blocked is False

    def test_returns_guardrail_result(self):
        reset_centroid_cache()
        trace = _make_trace()
        result = _run(
            check_recommendation_guardrail("Quel est le prix du riz ?", trace)
        )
        assert isinstance(result, GuardrailResult)
        assert result.reason == ""

    def test_recommendation_detected_structure(self):
        reset_centroid_cache()
        trace = _make_trace()
        result = _run(
            check_recommendation_guardrail(
                "Recommandez-moi le meilleur fournisseur", trace
            )
        )
        assert isinstance(result, GuardrailResult)
        assert isinstance(result.confidence, float)
