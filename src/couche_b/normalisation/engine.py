"""M-NORMALISATION-ENGINE -- Read-only deterministic alias normalisation.

Strategie (ordre strict) :
  1. s = alias_raw.strip()
  2. k = _to_ascii_lower(s)   (casefold + NFKD : suppression diacritiques)
  3. Tentative A : exact match sur alias_raw  (forme brute seedee)
  4. Tentative B : exact match sur normalized_alias (forme ASCII seedee)
  5. None si aucune correspondance

normalize_batch() : 1 seule requete DB, pas de N+1.
Aucun write DB. Aucun fuzzy/trigram.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence

from src.db.connection import get_db_cursor

_SQL_BATCH = """
    SELECT alias_raw, normalized_alias, item_id
    FROM couche_b.procurement_dict_aliases
    WHERE alias_raw        = ANY(%(raw_keys)s)
       OR normalized_alias = ANY(%(norm_keys)s)
"""


def _to_ascii_lower(s: str) -> str:
    """casefold + suppression des marques diacritiques (NFKD)."""
    nkfd = unicodedata.normalize("NFKD", s.casefold())
    return "".join(c for c in nkfd if unicodedata.category(c) != "Mn")


def normalize(alias_raw: str) -> str | None:
    """Normalise un alias vers son item_id. Retourne None si inconnu."""
    return normalize_batch([alias_raw]).get(alias_raw)


def normalize_batch(aliases: Sequence[str]) -> dict[str, str | None]:
    """Normalise une liste d'aliases vers leurs item_ids.

    1 seule requete DB (pas de N+1).
    Retourne un dict {alias_original: item_id | None}.
    """
    if not aliases:
        return {}

    # Pre-calcul des cles candidates
    candidates: list[tuple[str, str, str]] = []
    result: dict[str, str | None] = {}

    for alias in aliases:
        s = alias.strip()
        k = _to_ascii_lower(s) if s else ""
        candidates.append((alias, s, k))
        result[alias] = None  # valeur par defaut

    raw_keys = [s for _, s, _ in candidates if s]
    norm_keys = [k for _, _, k in candidates if k]

    if not raw_keys and not norm_keys:
        return result

    # Requete unique : Tentative A (alias_raw) + Tentative B (normalized_alias)
    with get_db_cursor() as cur:
        cur.execute(_SQL_BATCH, {"raw_keys": raw_keys, "norm_keys": norm_keys})
        rows = cur.fetchall()

    raw_map: dict[str, str] = {}  # alias_raw       -> item_id
    norm_map: dict[str, str] = {}  # normalized_alias -> item_id
    for row in rows:
        raw_map[row["alias_raw"]] = row["item_id"]
        norm_map[row["normalized_alias"]] = row["item_id"]

    # Reconstruction : Tentative A en priorite, puis B
    for alias, s, k in candidates:
        if not s:
            result[alias] = None
        elif s in raw_map:
            result[alias] = raw_map[s]
        elif k and k in norm_map:
            result[alias] = norm_map[k]
        else:
            result[alias] = None

    return result
