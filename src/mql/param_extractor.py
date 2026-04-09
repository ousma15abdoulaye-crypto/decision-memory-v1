"""MQL Parameter Extractor — Canon V5.1.0 Section 8.4.

Extraction déterministe des paramètres depuis une question en langage naturel.
INV-A03 : l'extraction de paramètres MQL utilise des règles déterministes (pas de LLM).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from uuid import UUID

from src.mql.templates import MQLParams

ZONE_KEYWORDS: dict[str, str] = {
    "bamako": "Bamako",
    "mopti": "Mopti",
    "sévaré": "Sévaré",
    "sevare": "Sévaré",
    "gao": "Gao",
    "ségou": "Ségou",
    "segou": "Ségou",
    "tombouctou": "Tombouctou",
    "kidal": "Kidal",
    "sikasso": "Sikasso",
    "kayes": "Kayes",
    "koulikoro": "Koulikoro",
}


async def extract_mql_params(query: str, tenant_id: UUID) -> MQLParams:
    """Extraction déterministe des paramètres depuis la question.

    Pas de LLM — règles simples et fiables (INV-A03).
    """
    query_lower = query.lower()

    zones = []
    for keyword, zone_name in ZONE_KEYWORDS.items():
        if keyword in query_lower:
            zones.append(zone_name)

    article = _extract_article(query_lower)

    vendor = None
    vendor_keywords = ["fournisseur", "vendor", "société", "sarl", "ets"]
    for kw in vendor_keywords:
        if kw in query_lower:
            match = re.search(rf"{kw}\s+(\w+)", query_lower)
            if match:
                vendor = match.group(1)
                break

    min_date = date(2025, 1, 1)
    year_match = re.search(r"20[2-3]\d", query)
    if year_match:
        year = int(year_match.group())
        min_date = date(year, 1, 1)

    quarter_match = re.search(r"[TQ]([1-4])\s*20[2-3]\d", query, re.IGNORECASE)
    start_date = None
    end_date = None
    if quarter_match and year_match:
        q = int(quarter_match.group(1))
        y = int(year_match.group())
        start_date = date(y, (q - 1) * 3 + 1, 1)
        end_month = q * 3
        if end_month == 12:
            end_date = date(y, 12, 31)
        else:
            end_date = date(y, end_month + 1, 1) - timedelta(days=1)

    proposed_price = None
    price_match = re.search(
        r"(\d[\d\s]*(?:\.\d+)?)\s*(?:fcfa|xof|cfa|francs?)", query_lower
    )
    if price_match:
        proposed_price = float(price_match.group(1).replace(" ", ""))

    return MQLParams(
        tenant_id=tenant_id,
        article_pattern=article,
        zones=zones or None,
        vendor_pattern=vendor,
        min_date=min_date,
        start_date=start_date,
        end_date=end_date,
        proposed_price=proposed_price,
    )


def _extract_article(query_lower: str) -> str:
    """Extrait l'article principal de la question."""
    stop_words = {
        "quel",
        "quelle",
        "quels",
        "quelles",
        "est",
        "le",
        "la",
        "les",
        "de",
        "du",
        "des",
        "un",
        "une",
        "prix",
        "coût",
        "cout",
        "médian",
        "median",
        "moyen",
        "moyenne",
        "combien",
        "tendance",
        "évolution",
        "evolution",
        "comparaison",
        "fournisseur",
        "fournisseurs",
        "zone",
        "à",
        "a",
        "ce",
        "cette",
        "trimestre",
        "mois",
        "année",
        "annee",
    }

    words = re.findall(r"\b[a-zéèêëàâùûôîïç]+\b", query_lower)
    meaningful = [w for w in words if w not in stop_words and len(w) > 2]

    if meaningful:
        return " ".join(meaningful[:3])
    return None
