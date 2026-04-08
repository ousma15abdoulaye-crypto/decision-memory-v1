"""Guardrail INV-W06 — Canon V5.1.0 Section 7.4.

Intercepte les tentatives de recommandation/classement AVANT tout appel LLM.
Confidence >= 0.85 sur le centroïde RECOMMENDATION -> bloqué.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agent.semantic_router import IntentClass, classify_intent


@dataclass
class GuardrailResult:
    blocked: bool
    confidence: float
    reason: str


async def check_recommendation_guardrail(query: str, trace: Any) -> GuardrailResult:
    """INV-W06 appliqué à l'agent.

    Intercepte les tentatives de recommandation AVANT tout appel LLM.
    Confidence >= 0.85 sur le centroïde RECOMMENDATION -> bloqué.
    """
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
