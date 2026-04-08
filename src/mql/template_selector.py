"""MQL Template Selector — Canon V5.1.0 Section 8.5.

Sélection déterministe du template SQL approprié basé sur les
paramètres extraits et les mots-clés de la question.
"""

from __future__ import annotations

from src.mql.templates import MQLParams


async def select_template(query: str, params: MQLParams) -> str:
    """Sélectionne le template SQL approprié (logique déterministe, pas de LLM)."""
    query_lower = query.lower()

    if any(
        kw in query_lower for kw in ["source", "campagne", "inventaire", "disponible"]
    ):
        return "T6_CAMPAIGN_INVENTORY"

    if params.proposed_price is not None:
        return "T5_ANOMALY_DETECTION"

    if params.vendor_pattern:
        return "T3_VENDOR_HISTORY"

    if any(
        kw in query_lower
        for kw in ["tendance", "évolution", "evolution", "depuis", "entre"]
    ):
        return "T2_PRICE_TREND"

    if params.zones and len(params.zones) >= 2:
        return "T4_ZONE_COMPARISON"
    if any(kw in query_lower for kw in ["comparaison", "comparer", "entre"]):
        return "T4_ZONE_COMPARISON"

    return "T1_PRICE_MEDIAN"
