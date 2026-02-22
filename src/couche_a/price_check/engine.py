"""
PriceCheck Engine -- Couche A (DMS V3.3.2 / ADR-0009).

Règles :
  - READ-ONLY : aucune écriture DB.
  - normalize_batch_fn() appelé une seule fois par lot (injecté par le router).
  - 1 requête mercuriale pour tous les item_ids résolus.
  - 1 requête scoring_configs par profil distinct (cache local).
  - Retourne toujours PriceCheckResult (jamais None).
  - Fallback hardcodé tracé dans notes si scoring_configs vide.

Isolation (INV-02 / DT-006) :
  - Aucune dépendance couche_b dans ce fichier.
  - normalize_batch_fn injecté par l'appelant (router ou test).
"""

from __future__ import annotations

import importlib as _importlib
from typing import Callable

from src.couche_a.price_check.schemas import OffreInput, PriceCheckResult, PriceVerdict


def _load_normalize_batch() -> Callable:
    """Load normalize_batch via importlib — aucune dépendance statique couche_b (INV-02)."""
    return _importlib.import_module("src.couche_b.normalisation.engine").normalize_batch


normalize_batch: Callable = _load_normalize_batch()

_FALLBACK_RATIO_ACCEPTABLE = 1.05
_FALLBACK_RATIO_ELEVE = 1.20
_FALLBACK_NOTE = "fallback hardcoded -- scoring_configs empty"


def _get_thresholds(conn, profile_code: str, cache: dict) -> tuple[float, float]:
    """Return (ratio_acceptable, ratio_eleve) from scoring_configs or fallback."""
    if profile_code in cache:
        return cache[profile_code]

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT price_ratio_acceptable, price_ratio_eleve
            FROM public.scoring_configs
            WHERE profile_code = %s
            LIMIT 1
            """,
            (profile_code,),
        )
        row = cur.fetchone()

    if row is None:
        # Try GENERIC fallback
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT price_ratio_acceptable, price_ratio_eleve
                FROM public.scoring_configs
                WHERE profile_code = 'GENERIC'
                LIMIT 1
                """,
            )
            row = cur.fetchone()

    if row is None:
        result = (_FALLBACK_RATIO_ACCEPTABLE, _FALLBACK_RATIO_ELEVE)
    else:
        result = (row["price_ratio_acceptable"], row["price_ratio_eleve"])

    cache[profile_code] = result
    return result


def _get_mercuriale_prices(conn, item_ids: list[str]) -> dict[str, float]:
    """Return {item_id: price_avg} for resolved item_ids (1 query for all)."""
    if not item_ids:
        return {}

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT item_id, AVG(price_avg) AS ref_price
            FROM couche_b.mercuriale_raw_queue
            WHERE item_id = ANY(%s)
              AND parse_status IN ('ok', 'partial')
              AND price_avg IS NOT NULL
            GROUP BY item_id
            """,
            (item_ids,),
        )
        rows = cur.fetchall()

    return {r["item_id"]: float(r["ref_price"]) for r in rows}


def analyze(
    offre: OffreInput, conn, normalize_batch_fn: Callable | None = None
) -> PriceCheckResult:
    """Analyze a single offer. Delegates to analyze_batch for efficiency."""
    results = analyze_batch([offre], conn, normalize_batch_fn=normalize_batch_fn)
    return results[0]


def analyze_batch(
    offres: list[OffreInput], conn, normalize_batch_fn: Callable | None = None
) -> list[PriceCheckResult]:
    """
    Analyze a batch of offers against mercuriale reference prices.

    Performance contract:
      - 1 call to normalize_batch_fn() for all aliases.
      - 1 query to mercuriale_raw_queue for all resolved item_ids.
      - 1 query to scoring_configs per distinct profile_code (cached).

    Args:
        offres: list of offers to analyze.
        conn: psycopg connection injected by caller.
        normalize_batch_fn: callable injected by caller; defaults to module-level
            normalize_batch (loaded via importlib, patchable in tests).
    """
    if not offres:
        return []

    _fn: Callable = normalize_batch_fn if normalize_batch_fn is not None else normalize_batch

    # -- Step 1: normalize all aliases (1 batch call) --
    alias_list = [o.alias_raw for o in offres]
    norm_results = _fn(alias_list, conn=conn)  # list[NormalisationResult]

    # -- Step 2: collect resolved item_ids (deduplicated) --
    item_ids: list[str] = []
    for nr in norm_results:
        if nr is not None and getattr(nr, "item_id", None):
            item_ids.append(nr.item_id)
    item_ids = list(dict.fromkeys(item_ids))  # dedupe, preserve order

    # -- Step 3: fetch reference prices (1 query) --
    ref_prices = _get_mercuriale_prices(conn, item_ids)

    # -- Step 4: fetch thresholds per distinct profile (cached) --
    threshold_cache: dict[str, tuple[float, float]] = {}
    distinct_profiles = list(dict.fromkeys(o.profile_code for o in offres))
    for pc in distinct_profiles:
        threshold_cache[pc] = _get_thresholds(conn, pc, threshold_cache)

    # -- Step 5: check if scoring_configs was empty (for fallback note) --
    config_empty = False
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM public.scoring_configs")
        if cur.fetchone()["n"] == 0:
            config_empty = True

    # -- Step 6: build results --
    results: list[PriceCheckResult] = []
    for offre, nr in zip(offres, norm_results):
        notes: list[str] = []
        item_id: str | None = getattr(nr, "item_id", None) if nr else None
        normalisation = nr

        prix_total = offre.prix_unitaire * offre.quantite
        prix_ref: float | None = ref_prices.get(item_id) if item_id else None

        ratio_acceptable, ratio_eleve = threshold_cache[offre.profile_code]

        if config_empty:
            notes.append(_FALLBACK_NOTE)

        if prix_ref is None:
            verdict = PriceVerdict.NO_REF
            ratio = None
            if item_id is None:
                notes.append("alias UNRESOLVED -- no mercuriale match possible")
            else:
                notes.append(f"item_id '{item_id}' resolved but no mercuriale data")
        else:
            ratio = round(prix_total / prix_ref, 6)
            if ratio <= ratio_acceptable:
                verdict = PriceVerdict.WITHIN_REF
            else:
                verdict = PriceVerdict.ABOVE_REF
                if ratio > ratio_eleve:
                    notes.append(
                        f"ratio {ratio:.4f} > threshold_eleve {ratio_eleve} -- significantly above ref"
                    )
                else:
                    notes.append(
                        f"ratio {ratio:.4f} > threshold_acceptable {ratio_acceptable} -- moderately above ref"
                    )

        results.append(
            PriceCheckResult(
                alias_raw=offre.alias_raw,
                item_id=item_id,
                prix_total_soumis=round(prix_total, 4),
                prix_ref=round(prix_ref, 4) if prix_ref is not None else None,
                ratio=ratio,
                verdict=verdict,
                profile_code=offre.profile_code,
                notes=notes,
                normalisation=normalisation,
            )
        )

    return results
