"""
Ingest Parser mercuriale — DMS V4.1.0

Parse le Markdown retourné par LlamaCloud (AsyncLlamaCloud) vers
des lignes structurées pour insertion DB.

RÈGLE-29 : ingestion brute · pas de normalisation
RÈGLE-21 : ce module ne fait aucun appel réseau
           _extract_markdown_llamacloud est dans importer.py (point de mock)

Séparé de parser.py (parser déterministe Couche B existant) pour éviter
toute collision de noms et préserver ADR-0002.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

# ── Patterns regex ──────────────────────────────────────────────────────────

# "Prix TTC, Kayes, 2024" ou "Prix TTC Mopti 2023"
_ZONE_HEADER_RE = re.compile(
    r"Prix\s+TTC[,\s]+([A-Za-zÀ-ÿ\s\-]+?)[,\s]+(\d{4})",
    re.IGNORECASE,
)

# "**1. Fournitures de bureau**" ou "1. Fournitures"
_GROUP_RE = re.compile(
    r"^\**\s*(\d+)\.\s+([A-Za-zÀ-ÿ\s\-\'\/\(\)]+?)\**\s*$",
)

# Ligne article avec 6 colonnes (code · label · unité · min · moy · max)
_ARTICLE_RE = re.compile(
    r"^\|?\s*(\d+\.\d+)\s*\|?\s*"
    r"(.+?)\s*\|?\s*"
    r"([A-Za-zÀ-ÿ\s\d\/\-\.]+?)\s*\|?\s*"
    r"([\d\s\u202f\xa0]+)\s*\|?\s*"
    r"([\d\s\u202f\xa0]+)\s*\|?\s*"
    r"([\d\s\u202f\xa0]+)\s*\|?\s*$",
)


def _clean_price(raw: str) -> Decimal | None:
    """Nettoie une valeur prix brute → Decimal · None si invalide."""
    if not raw:
        return None
    cleaned = re.sub(r"[\s\u202f\xa0]", "", raw.strip())
    if not cleaned or not re.match(r"^\d+$", cleaned):
        return None
    try:
        d = Decimal(cleaned)
        return d if d > 0 else None
    except InvalidOperation:
        return None


def _extract_zone_from_header(text: str) -> str | None:
    """Extrait le nom de zone depuis un en-tête colonne prix."""
    m = _ZONE_HEADER_RE.search(text)
    return m.group(1).strip() if m else None


def parse_markdown_to_lines(
    markdown: str,
    year: int,
    default_zone_raw: str | None = None,
) -> list[dict[str, Any]]:
    """
    Parse le Markdown LlamaCloud → liste de dicts mercurials.
    Retourne sans source_id (ajouté par l'importer).

    Gère :
      2024 : bloc par zone (en-tête change dans le PDF)
      2023 : classé par région (zone fournie via default_zone_raw)
    """
    lines_out: list[dict[str, Any]] = []
    current_zone = default_zone_raw
    current_group = None

    for raw_line in markdown.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        # Détection zone
        zone = _extract_zone_from_header(line)
        if zone:
            current_zone = zone
            logger.debug("Zone : %s", current_zone)
            continue

        # Détection groupe
        gm = _GROUP_RE.match(line)
        if gm:
            current_group = gm.group(2).strip()
            logger.debug("Groupe : %s", current_group)
            continue

        # Détection article
        am = _ARTICLE_RE.match(line)
        if not am:
            continue

        label = am.group(2).strip()
        unit_raw = am.group(3).strip()
        if not label:
            continue

        price_min = _clean_price(am.group(4))
        price_avg = _clean_price(am.group(5))
        price_max = _clean_price(am.group(6))

        if price_avg is None:
            continue

        # Fallback si min ou max manquants
        price_min = price_min or price_avg
        price_max = price_max or price_avg

        # Calcul confidence
        confidence = 1.0
        metadata: dict[str, Any] = {}

        if not current_zone:
            confidence -= 0.15
            metadata["zone_missing"] = True

        if price_min == price_avg == price_max:
            confidence -= 0.10
            metadata["single_price"] = True

        if not (price_min <= price_avg <= price_max):
            metadata["price_order_violation"] = True
            metadata["raw_prices"] = {
                "min": float(price_min),
                "avg": float(price_avg),
                "max": float(price_max),
            }

        confidence = max(0.0, round(confidence, 3))

        lines_out.append(
            {
                "item_code": am.group(1).strip(),
                "item_canonical": label,
                "group_label": current_group,
                "price_min": price_min,
                "price_avg": price_avg,
                "price_max": price_max,
                "currency": "XOF",
                "unit_raw": unit_raw or None,
                "zone_raw": current_zone,
                "year": year,
                "confidence": confidence,
                "review_required": confidence < 0.80,
                "extraction_metadata": metadata,
            }
        )

    logger.info("IngestParser · %d lignes extraites", len(lines_out))
    return lines_out
