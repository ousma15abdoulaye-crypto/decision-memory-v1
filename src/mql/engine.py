"""MQL Engine V8 — Canon V5.1.0 Section 8.3.

Pipeline complet : extract params -> select template -> execute SQL -> collect sources.
INV-A02 : zéro concaténation SQL — uniquement des bind params.
INV-A04 : chaque réponse MQL liste ses sources.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from src.mql.param_extractor import extract_mql_params
from src.mql.template_selector import select_template
from src.mql.templates import MQL_TEMPLATES, MQLParams


@dataclass
class MQLSource:
    name: str
    source_type: str
    publisher: str
    published_date: date | None
    is_official: bool


@dataclass
class MQLResult:
    template_used: str
    rows: list[dict[str, Any]]
    row_count: int
    sources: list[MQLSource]
    confidence: float
    latency_ms: int
    params_used: dict[str, Any]


async def execute_mql_query(
    db: Any,
    tenant_id: UUID,
    workspace_id: UUID | None,
    query: str,
    context: Any,
) -> MQLResult:
    """Exécute une requête MQL complète (Canon Section 8.3).

    1. Extraire les paramètres de la question en langage naturel
    2. Sélectionner le template SQL approprié
    3. Exécuter la requête paramétrée (INV-A02)
    4. Collecter les sources (INV-A04)
    5. Retourner le résultat structuré
    """
    start = time.monotonic()

    params: MQLParams = await extract_mql_params(query, tenant_id)

    template_key = await select_template(query, params)
    template = MQL_TEMPLATES[template_key]

    bind_params: dict[str, Any] = {
        "tenant_id": tenant_id,
        "article_pattern": (
            f"%{params.article_pattern}%" if params.article_pattern else "%"
        ),
        "zones": params.zones or ["Bamako", "Mopti", "Sévaré", "Gao"],
        "vendor_pattern": (
            f"%{params.vendor_pattern}%" if params.vendor_pattern else "%"
        ),
        "min_date": params.min_date or date(2025, 1, 1),
        "start_date": params.start_date or date(2025, 1, 1),
        "end_date": params.end_date or date.today(),
        "proposed_price": params.proposed_price or 0,
        "zone": params.zones[0] if params.zones else None,
        "max_results": params.max_results,
    }

    rows = await db.fetch_all(template["sql"], bind_params)
    rows_dict = [dict(r) for r in rows]

    sources_seen: set[str] = set()
    sources: list[MQLSource] = []
    for row in rows_dict:
        src_key = row.get("campaign_name") or row.get("name")
        if src_key and src_key not in sources_seen:
            sources_seen.add(src_key)
            sources.append(
                MQLSource(
                    name=src_key,
                    source_type=row.get("source_type", "unknown"),
                    publisher=row.get("publisher", "unknown"),
                    published_date=row.get("published_date"),
                    is_official=row.get("is_official", False),
                )
            )

    elapsed_ms = int((time.monotonic() - start) * 1000)

    confidence = _compute_mql_confidence(rows_dict, sources)

    return MQLResult(
        template_used=template_key,
        rows=rows_dict,
        row_count=len(rows_dict),
        sources=sources,
        confidence=confidence,
        latency_ms=elapsed_ms,
        params_used={
            "article": params.article_pattern,
            "zones": params.zones,
            "vendor": params.vendor_pattern,
        },
    )


def _compute_mql_confidence(
    rows: list[dict[str, Any]], sources: list[MQLSource]
) -> float:
    """Confiance basée sur le volume de données et la qualité des sources."""
    if not rows:
        return 0.0

    base = min(0.5, len(rows) / 20.0)

    official_bonus = 0.3 if any(s.is_official for s in sources) else 0.0
    multi_source_bonus = 0.2 if len(sources) >= 2 else 0.0

    return min(1.0, base + official_bonus + multi_source_bonus)
