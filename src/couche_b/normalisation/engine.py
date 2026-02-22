"""M-NORMALISATION-ENGINE -- Read-only deterministic alias normalisation.

Strategie (ordre strict) :
  1. s = alias_raw.strip()
  2. k = _to_ascii_lower(s)   (casefold + NFKD : suppression diacritiques)
  3. Tentative A : exact match sur alias_raw       -> EXACT_ALIAS_RAW,      score=1.0
  4. Tentative B : exact match sur normalized_alias -> EXACT_NORMALIZED_ALIAS, score=1.0
  5. Aucun hit                                      -> UNRESOLVED,            score=0.0

ARCH-001 : Zéro write DB.
PERF-001 : 1 requete batch (pas de N+1).
NFKD-001 : _to_ascii_lower() conserve (casefold + NFKD).
ARCH-002 : normalize() retourne TOUJOURS NormalisationResult (jamais None).

La connexion est injectee par l'appelant (pas d'ouverture DB dans engine).
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence

from src.couche_b.normalisation.schemas import NormalisationResult, NormStrategy

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


def normalize(alias_raw: str, conn) -> NormalisationResult:
    """Normalise un alias. Retourne TOUJOURS un NormalisationResult (jamais None).

    Args:
        alias_raw: alias brut a normaliser.
        conn: connexion psycopg injectee par l'appelant (pas d'ouverture DB ici).
    """
    results = normalize_batch([alias_raw], conn)
    return results[0]


def normalize_batch(aliases: Sequence[str], conn) -> list[NormalisationResult]:
    """Normalise une liste d'aliases. 1 seule requete DB (PERF-001).

    Args:
        aliases: liste d'aliases bruts.
        conn: connexion psycopg injectee par l'appelant.

    Returns:
        list[NormalisationResult] dans le meme ordre que aliases.
        Jamais None, jamais d'exception sur input inconnu.
    """
    # Pre-calcul des cles candidates
    candidates: list[tuple[str, str, str]] = []
    for alias in aliases:
        s = alias.strip()
        k = _to_ascii_lower(s) if s else ""
        candidates.append((alias, s, k))

    raw_keys = [s for _, s, _ in candidates if s]
    norm_keys = [k for _, _, k in candidates if k]

    raw_map: dict[str, str] = {}
    norm_map: dict[str, str] = {}

    if raw_keys or norm_keys:
        with conn.cursor() as cur:
            cur.execute(_SQL_BATCH, {"raw_keys": raw_keys, "norm_keys": norm_keys})
            for row in cur.fetchall():
                raw_map[row["alias_raw"]] = row["item_id"]
                norm_map[row["normalized_alias"]] = row["item_id"]

    results: list[NormalisationResult] = []
    for alias, s, k in candidates:
        normalized_input = k  # forme NFKD
        if not s:
            results.append(
                NormalisationResult(
                    input_raw=alias,
                    normalized_input=normalized_input,
                    item_id=None,
                    strategy=NormStrategy.UNRESOLVED,
                    score=0.0,
                )
            )
        elif s in raw_map:
            results.append(
                NormalisationResult(
                    input_raw=alias,
                    normalized_input=normalized_input,
                    item_id=raw_map[s],
                    strategy=NormStrategy.EXACT_ALIAS_RAW,
                    score=1.0,
                )
            )
        elif k and k in norm_map:
            results.append(
                NormalisationResult(
                    input_raw=alias,
                    normalized_input=normalized_input,
                    item_id=norm_map[k],
                    strategy=NormStrategy.EXACT_NORMALIZED_ALIAS,
                    score=1.0,
                )
            )
        else:
            results.append(
                NormalisationResult(
                    input_raw=alias,
                    normalized_input=normalized_input,
                    item_id=None,
                    strategy=NormStrategy.UNRESOLVED,
                    score=0.0,
                )
            )

    return results
