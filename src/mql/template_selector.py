"""MQL Template Selector — Canon V5.1.0 Section 8.5.

Sélection déterministe du template SQL approprié basé sur les
paramètres extraits et les mots-clés de la question.
"""

from __future__ import annotations

from src.mql.templates import MQLParams


async def select_template(query: str, params: MQLParams) -> str:
    """Sélectionne le template SQL approprié (logique déterministe, pas de LLM)."""
    query_lower = query.lower()

    # ADR-V53 : agrégat M9 (market_signals_v2) — avant enquêtes / campagnes.
    if any(
        kw in query_lower
        for kw in (
            "signal agrégé",
            "signal agrege",
            "référence marché",
            "reference marche",
            "prix de référence marché",
            "prix de reference marche",
            "mercuriale agrégée",
            "mercuriale agrege",
            " m9 ",
            "market_signals",
            "formule m9",
        )
    ):
        return "T7_MSV2_REFERENCE"

    if any(
        kw in query_lower for kw in ["source", "campagne", "inventaire", "disponible"]
    ):
        return "T6_CAMPAIGN_INVENTORY"

    if params.proposed_price is not None:
        return "T5_ANOMALY_DETECTION"

    if params.vendor_pattern:
        return "T3_VENDOR_HISTORY"

    if params.zones and len(params.zones) >= 2:
        return "T4_ZONE_COMPARISON"
    if any(kw in query_lower for kw in ["comparaison", "comparer"]):
        return "T4_ZONE_COMPARISON"

    if any(
        kw in query_lower
        for kw in ["tendance", "évolution", "evolution", "depuis", "entre"]
    ):
        return "T2_PRICE_TREND"

    if params.start_date or params.end_date:
        return "T2_PRICE_TREND"

    return "T1_PRICE_MEDIAN"
