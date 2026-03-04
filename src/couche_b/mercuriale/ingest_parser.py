"""
Ingest Parser mercuriale — DMS V4.1.0

Parse le HTML retourné par LlamaCloud (AsyncLlamaCloud · tier agentic)
vers des lignes structurées pour insertion DB.

Format réel confirmé (probe 2026-03-04) :
  LlamaCloud agentic produit des TABLEAUX HTML (<table>/<tr>/<td>),
  pas des tableaux Markdown pipes (|col|col|).

  Structure par table :
    <thead> <th colspan="7">Groupe N : Libellé</th> </thead>
    <tr> header colonnes (colspan → < 7 tds) </tr>
    <tr> sous-groupe + Minimum/Moyen/Maximum (7 tds) </tr>
    <tr> données : [grp_num, item_code, designation, unit, min, moy, max] </tr>
    ...

  Zone extraite depuis :
    1. <mark>***ZONE***</mark>  (en-tête document)
    2. "Prix TTC, Zone, Année"  (header colonne dans <td colspan="3">)

RÈGLE-29 : ingestion brute · pas de normalisation
RÈGLE-21 : ce module ne fait aucun appel réseau
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

# ── Patterns ────────────────────────────────────────────────────────────────

# Zone depuis <mark>***BOUGOUNI***</mark>  (bold optionnel)
_MARK_ZONE_RE = re.compile(
    r"<mark>\*{0,3}([A-Za-zÀ-ÿ\s\-]+?)\*{0,3}</mark>",
    re.IGNORECASE,
)

# Zone depuis "Prix TTC, Bougouni, 2023" dans un <td>
_TTC_ZONE_RE = re.compile(
    r"Prix\s+TTC[,\s]+([A-Za-zÀ-ÿ\s\-]+?)[,\s]+(\d{4})",
    re.IGNORECASE,
)

# Groupe depuis <th ...>Groupe N : Libellé</th>
_GROUP_TH_RE = re.compile(
    r"<th[^>]*>Groupe\s+\d+\s*:\s*([^<]+)</th>",
    re.IGNORECASE,
)

# Tous les blocs <tr>...</tr>
_TR_RE = re.compile(r"<tr>(.*?)</tr>", re.DOTALL | re.IGNORECASE)

# Contenu de chaque <td>...</td>  (attributs éventuels ignorés)
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL | re.IGNORECASE)

# Mots qui signalent une ligne d'en-tête (pas de données)
_HEADER_WORDS = frozenset(
    ["minimum", "moyen", "maximum", "designations", "codes", "unité", "unite"]
)


def _strip_html(text: str) -> str:
    """Supprime les balises HTML et normalise les espaces."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _clean_price(raw: str) -> Decimal | None:
    """
    Nettoie un prix brut → Decimal.
    Gère les séparateurs de milliers : espaces, \\xa0, \\u202f.
    Retourne None si invalide ou nul.
    """
    if not raw:
        return None
    cleaned = re.sub(r"[\s\u202f\xa0]", "", raw.strip())
    if not cleaned or not re.match(r"^\d+(\.\d+)?$", cleaned):
        return None
    try:
        d = Decimal(cleaned)
        return d if d > 0 else None
    except InvalidOperation:
        return None


def _extract_zone_from_header(text: str) -> str | None:
    """Extrait le nom de zone depuis un texte 'Prix TTC, Zone, Année'."""
    m = _TTC_ZONE_RE.search(text)
    return m.group(1).strip() if m else None


def parse_markdown_to_lines(
    markdown: str,
    year: int,
    default_zone_raw: str | None = None,
) -> list[dict[str, Any]]:
    """
    Parse le HTML produit par LlamaCloud (tier agentic) → liste de dicts
    prêts pour insertion dans la table mercurials.

    Retourne sans source_id (ajouté par l'importer).

    Gère :
      2024 : PDF combiné · zone dans chaque table (Prix TTC, Zone, Année)
      2023 : PDFs individuels · zone dans <mark> ou default_zone_raw
    """
    lines_out: list[dict[str, Any]] = []
    current_zone = default_zone_raw
    current_group: str | None = None

    # ── 1. Zone globale depuis <mark> ────────────────────────────────────────
    mark_m = _MARK_ZONE_RE.search(markdown)
    if mark_m:
        zone_candidate = mark_m.group(1).strip().title()
        if zone_candidate:
            current_zone = zone_candidate
            logger.debug("Zone <mark> : %s", current_zone)

    # ── 2. Découpe par blocs <table> ─────────────────────────────────────────
    table_blocks = re.split(r"<table[^>]*>", markdown, flags=re.IGNORECASE)

    for block in table_blocks[1:]:  # [0] = contenu avant le premier <table>
        # Groupe depuis <thead> / <th>
        th_m = _GROUP_TH_RE.search(block)
        if th_m:
            current_group = _strip_html(th_m.group(1)).strip()
            logger.debug("Groupe : %s", current_group)

        # Zone dans le header de la table (Prix TTC, Zone, Année)
        zone_in_table = _extract_zone_from_header(block)
        if zone_in_table:
            current_zone = zone_in_table
            logger.debug("Zone TTC : %s", current_zone)

        # ── 3. Lignes <tr> ───────────────────────────────────────────────────
        for row_html in _TR_RE.findall(block):
            tds_raw = _TD_RE.findall(row_html)
            if len(tds_raw) < 7:
                # Lignes d'en-tête avec colspan → moins de 7 <td> réels
                continue

            cells = [_strip_html(td) for td in tds_raw]

            # Ignorer les lignes d'en-tête (Minimum/Moyen/Maximum etc.)
            lower_cells = {c.lower() for c in cells}
            if lower_cells & _HEADER_WORDS:
                # Récupérer le libellé du sous-groupe (cells[2])
                if cells[2] and cells[2].lower() not in _HEADER_WORDS:
                    current_group = cells[2]
                continue

            # ── Ligne de données : [grp, code, label, unit, min, moy, max] ──
            item_code = cells[1].strip() or None
            item_canonical = cells[2].strip()
            unit_raw = cells[3].strip() or None

            if not item_canonical:
                continue

            price_min = _clean_price(cells[4])
            price_avg = _clean_price(cells[5])
            price_max = _clean_price(cells[6])

            if price_avg is None:
                continue

            price_min = price_min or price_avg
            price_max = price_max or price_avg

            # ── Confidence & metadata ─────────────────────────────────────
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
                    "item_code": item_code,
                    "item_canonical": item_canonical,
                    "group_label": current_group,
                    "price_min": price_min,
                    "price_avg": price_avg,
                    "price_max": price_max,
                    "currency": "XOF",
                    "unit_raw": unit_raw,
                    "zone_raw": current_zone,
                    "year": year,
                    "confidence": confidence,
                    "review_required": confidence < 0.80,
                    "extraction_metadata": metadata,
                }
            )

    logger.info("IngestParser · %d lignes extraites", len(lines_out))
    return lines_out
