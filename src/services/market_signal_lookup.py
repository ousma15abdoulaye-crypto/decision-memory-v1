"""Lookup prix de référence marché agrégé (M9) — ADR-V53.

Source unique de vérité pour la résolution item×zone → ``price_seasonal_adj``
utilisée par ``market_delta`` et alignée sémantiquement avec MQL T7.

Voir : ``docs/adr/ADR-V53-MARKET-READ-MODEL.md``.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from typing import Any

from src.db import db_execute_one

# Même seuil que l’historique ``market_delta`` (pg_trgm).
ITEM_SIMILARITY_THRESHOLD = 0.55


def normalize_label_to_item_slug(label: str) -> str:
    """Normalise un libellé article en slug compatible ``market_signals_v2.item_id``.

    NFD → ASCII, lowercase, non-alphanum → ``_``, strip bords.
    """
    nfkd = unicodedata.normalize("NFKD", label)
    ascii_str = nfkd.encode("ascii", errors="ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_str.lower().strip())
    return slug.strip("_")


def lookup_market_price_seasonal_adj(
    conn: Any,
    item_slug: str,
    zone_id: str,
) -> Decimal | None:
    """Retourne ``price_seasonal_adj`` pour (zone_id, item) depuis ``market_signals_v2``.

    Passe 1 : match exact ``item_id = slug``.
    Passe 2 : ``similarity(item_id, slug) > ITEM_SIMILARITY_THRESHOLD`` (pg_trgm).

    Args:
        conn: Connexion synchrone (wrapper DMS).
        item_slug: Slug normalisé (voir ``normalize_label_to_item_slug``).
        zone_id: Identifiant zone (``geo_master.id`` / ``process_workspaces.zone_id``).
    """
    row = db_execute_one(
        conn,
        """
        SELECT price_seasonal_adj
        FROM market_signals_v2
        WHERE zone_id = :zone
          AND signal_quality IN ('strong', 'moderate', 'propagated')
          AND (
              item_id = :slug
              OR (set_limit(:threshold) IS NOT NULL AND similarity(item_id, :slug) > :threshold)
          )
        ORDER BY
            CASE WHEN item_id = :slug THEN 0 ELSE 1 END,
            similarity(item_id, :slug) DESC
        LIMIT 1
        """,
        {
            "zone": zone_id,
            "slug": item_slug,
            "threshold": float(ITEM_SIMILARITY_THRESHOLD),
        },
    )
    if row and row.get("price_seasonal_adj") is not None:
        try:
            return Decimal(str(row["price_seasonal_adj"]))
        except Exception:
            return None
    return None
