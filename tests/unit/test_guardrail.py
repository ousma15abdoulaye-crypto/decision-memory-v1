"""Tests Guardrail INV-W06 — Canon V5.1.0 Section 7.4, Locking test 15.

Vérifie que le guardrail bloque les tentatives de recommandation
et laisse passer les requêtes légitimes.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from src.agent.guardrail import GuardrailResult, check_recommendation_guardrail
from src.agent.semantic_router import IntentClass, reset_centroid_cache


def _run(coro):
    return asyncio.run(coro)


def _make_trace():
    trace = MagicMock()
    span = MagicMock()
    trace.span.return_value = span
    return trace


class TestGuardrailResult:
    def test_not_blocked_for_market_query(self):
        reset_centroid_cache()
        trace = _make_trace()
        for q in (
            "prix du ciment à Bamako",
            "Quel est le prix du ciment à Bamako ?",
            "ciment prix Bamako",
        ):
            result = _run(check_recommendation_guardrail(q, trace))
            assert isinstance(result, GuardrailResult)
            assert result.blocked is False, f"unexpected block for: {q!r}"

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

    def test_recommendation_blocked_when_high_confidence(self):
        """INV-W06 locking test: recommendation with sim >= 0.85 MUST be blocked."""
        from unittest.mock import patch

        from src.agent.semantic_router import IntentResult

        fake_result = IntentResult(
            intent_class=IntentClass.RECOMMENDATION,
            confidence=0.92,
        )
        reset_centroid_cache()
        trace = _make_trace()
        with patch(
            "src.agent.guardrail.classify_intent",
            return_value=fake_result,
        ):
            result = _run(
                check_recommendation_guardrail(
                    "Quel fournisseur dois-je choisir?", trace
                )
            )
        assert result.blocked is True
        assert result.confidence >= 0.85

    def test_price_query_not_blocked_even_if_embedding_says_recommendation(self):
        """Heuristique prix avant embeddings — faux positif Mistral corrigé."""
        from unittest.mock import patch

        from src.agent.semantic_router import IntentResult

        fake_result = IntentResult(
            intent_class=IntentClass.RECOMMENDATION,
            confidence=0.95,
        )
        reset_centroid_cache()
        trace = _make_trace()
        with patch(
            "src.agent.guardrail.classify_intent",
            return_value=fake_result,
        ):
            result = _run(
                check_recommendation_guardrail(
                    "Prix du ciment à Bamako ce mois ?", trace
                )
            )
        assert result.blocked is False

    def test_recommendation_not_blocked_below_threshold(self):
        """INV-W06: sim < 0.85 on RECOMMENDATION should NOT block."""
        from unittest.mock import patch

        from src.agent.semantic_router import IntentResult

        fake_result = IntentResult(
            intent_class=IntentClass.RECOMMENDATION,
            confidence=0.70,
        )
        reset_centroid_cache()
        trace = _make_trace()
        with patch(
            "src.agent.guardrail.classify_intent",
            return_value=fake_result,
        ):
            result = _run(
                check_recommendation_guardrail(
                    "Quel fournisseur dois-je choisir?", trace
                )
            )
        assert result.blocked is False
