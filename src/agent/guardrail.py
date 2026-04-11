"""Guardrail INV-W06 — Canon V5.1.0 Section 7.4 (pré-LLM).

Intercepte les recommandations AVANT tout appel LLM uniquement si
``AGENT_INV_W06_PRE_LLM_BLOCK`` est true (désactivé par défaut).

Le filtre de sortie et les invariants API (pas de winner/rank) restent actifs.
Voir docs/ops/TECHNICAL_DEBT.md (TD-AGENT-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agent.market_query_lexicon import looks_like_factual_market_price_query
from src.agent.semantic_router import IntentClass, classify_intent
from src.core.config import get_settings


@dataclass
class GuardrailResult:
    blocked: bool
    confidence: float
    reason: str


async def check_recommendation_guardrail(query: str, trace: Any) -> GuardrailResult:
    """INV-W06 pré-LLM : 422 si RECOMMENDATION et sim >= 0,85 (si flag activé).

    Sans ``AGENT_INV_W06_PRE_LLM_BLOCK=true``, retour immédiat sans embedding.

    Court-circuit prix factuel : avant embeddings si le pré-LLM est activé.
    """
    if not get_settings().AGENT_INV_W06_PRE_LLM_BLOCK:
        return GuardrailResult(blocked=False, confidence=0.0, reason="")

    if looks_like_factual_market_price_query(query):
        return GuardrailResult(blocked=False, confidence=0.0, reason="")

    intent = await classify_intent(query)

    if intent.intent_class == IntentClass.RECOMMENDATION and intent.confidence >= 0.85:
        span = trace.span(
            name="guardrail_inv_w06",
            input={"query": query, "confidence": intent.confidence},
            output={"blocked": True},
        )
        span.update(tags=["guardrail_inv_w06"])
        span.end()

        return GuardrailResult(
            blocked=True,
            confidence=intent.confidence,
            reason="Tentative de recommandation détectée",
        )

    return GuardrailResult(blocked=False, confidence=0.0, reason="")
