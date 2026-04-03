#!/usr/bin/env python3
"""
batch_signal_from_map.py — V4 Activation Wartime M15.

Calcule les signaux marche sur TOUTES les paires (dict_item_id x zone_id)
issues de mercurials_item_map x tracked_market_zones.

Difference avec compute_market_signals.py :
  - compute_market_signals.py : scope = tracked_market_items x tracked_market_zones
    -> ~82 items distincts couverts (5.5% du dictionnaire)
  - batch_signal_from_map.py : scope = mercurials_item_map.dict_item_id x tracked_market_zones
    -> jusqu'a 1004 items couverts (cible : 65% du dictionnaire)

Usage :
  # Dry-run (sans ecriture) — mesure le scope calculable
  python scripts/with_railway_env.py python scripts/batch_signal_from_map.py --dry-run

  # Run reel sur Railway
  python scripts/with_railway_env.py python scripts/batch_signal_from_map.py --apply

  # Limiter a N paires (test partiel)
  python scripts/with_railway_env.py python scripts/batch_signal_from_map.py --apply --limit 500

Gate de sortie V4 :
  SELECT COUNT(DISTINCT item_id) FROM public.market_signals_v2 >= 650
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", os.environ.get("RAILWAY_DATABASE_URL", ""))
    if not url:
        raise SystemExit(
            f"{RED}[ERR]{RESET} DATABASE_URL ou RAILWAY_DATABASE_URL manquante.\n"
            "  Lancer via : python scripts/with_railway_env.py python scripts/batch_signal_from_map.py --dry-run"
        )
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres://", "postgresql://", 1
    )


def _get_scope(cur, limit: int | None) -> list[tuple[str, str]]:
    """Scope optimise : items avec prix dans market_surveys x tracked_market_zones.

    Filtre uniquement les items qui ont des donnees de prix reelles dans
    market_surveys (price_per_unit > 0). Evite 9000+ paires vides.
    496 items x 19 zones = ~9424 paires significatives vs 19076 paires
    dont 9652 produiraient des signaux "empty".
    """
    query = """
        SELECT DISTINCT ms.item_id, tmz.zone_id
        FROM public.market_surveys ms
        CROSS JOIN public.tracked_market_zones tmz
        WHERE ms.item_id IS NOT NULL
          AND ms.price_per_unit > 0
          AND EXISTS (
              SELECT 1 FROM public.mercurials_item_map mim
              WHERE mim.dict_item_id = ms.item_id
          )
        ORDER BY ms.item_id, tmz.zone_id
    """
    if limit:
        query += f" LIMIT {int(limit)}"

    cur.execute(query)
    return [(r["item_id"], r["zone_id"]) for r in cur.fetchall()]


def _preload_taxo(cur) -> dict[str, str | None]:
    """Charge tous les item_id->taxo_l3 en une seule requete (evite N round-trips)."""
    cur.execute(
        "SELECT item_id, taxo_l3 FROM couche_b.procurement_dict_items "
        "WHERE taxo_l3 IS NOT NULL"
    )
    return {r["item_id"]: r["taxo_l3"] for r in cur.fetchall()}


def _probe_pre(cur) -> dict:
    """Mesure l'etat avant le batch."""
    cur.execute("SELECT COUNT(DISTINCT dict_item_id) FROM public.mercurials_item_map")
    items_in_map = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) FROM public.tracked_market_zones")
    zones = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(DISTINCT item_id) FROM public.market_signals_v2")
    items_with_signal = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) FROM couche_b.procurement_dict_items")
    dict_total = cur.fetchone()["count"]

    return {
        "items_in_map": items_in_map,
        "zones": zones,
        "items_with_signal_before": items_with_signal,
        "dict_total": dict_total,
    }


def _probe_post(cur) -> dict:
    """Mesure l'etat apres le batch."""
    cur.execute("SELECT COUNT(DISTINCT item_id) FROM public.market_signals_v2")
    items_with_signal = cur.fetchone()["count"]

    cur.execute(
        "SELECT signal_quality, COUNT(*) as cnt "
        "FROM public.market_signals_v2 "
        "GROUP BY signal_quality ORDER BY cnt DESC"
    )
    quality_dist = {r["signal_quality"]: r["cnt"] for r in cur.fetchall()}

    cur.execute("SELECT COUNT(*) FROM couche_b.procurement_dict_items")
    dict_total = cur.fetchone()["count"]

    return {
        "items_with_signal_after": items_with_signal,
        "quality_distribution": quality_dist,
        "dict_total": dict_total,
        "coverage_pct": round(items_with_signal * 100 / max(dict_total, 1), 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch signal depuis mercurials_item_map (V4 Wartime M15)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Mode simulation sans ecriture (defaut)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ecriture reelle en base (desactive dry-run)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limiter le nombre de paires traitees (test partiel)",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=100,
        help="Loguer les statistiques tous les N paires (defaut: 100)",
    )
    args = parser.parse_args()

    dry_run = not args.apply

    print(f"\n{BOLD}BATCH SIGNAL ENGINE — mercurials_item_map scope (V4 M15){RESET}")
    print(
        f"Mode : {'DRY-RUN (sans ecriture)' if dry_run else 'APPLY (ecriture reelle)'}"
    )
    print()

    try:
        import psycopg
        from psycopg.rows import dict_row

        from src.couche_a.market.signal_engine import SignalEngine
    except ImportError as exc:
        print(f"{RED}[ERR]{RESET} Import manquant : {exc}", file=sys.stderr)
        return 1

    db_url = _get_db_url()
    print(
        f"  DB : {db_url.split('@')[-1].split('/')[0] if '@' in db_url else db_url[:40]}"
    )

    conn = psycopg.connect(db_url, row_factory=dict_row)
    cur = conn.cursor()
    engine = SignalEngine(db_url, allow_railway=True)

    # Probe pre-batch
    logger.info("Probe pre-batch...")
    pre = _probe_pre(cur)
    logger.info(
        "Scope : %d items dans mercurials_item_map x %d zones = ~%d paires theoriques",
        pre["items_in_map"],
        pre["zones"],
        pre["items_in_map"] * pre["zones"],
    )
    logger.info(
        "Avant batch : %d items avec signal (couverture %.1f%%)",
        pre["items_with_signal_before"],
        pre["items_with_signal_before"] * 100 / max(pre["dict_total"], 1),
    )

    # Pre-charger taxo_l3 en une seule requete (elimine N round-trips individuels)
    logger.info("Pre-chargement taxo_l3 (1 requete bulk)...")
    taxo_cache = _preload_taxo(cur)
    logger.info("taxo_l3 cache : %d items charges", len(taxo_cache))

    # Charger le scope optimise (items avec prix reels uniquement)
    logger.info("Chargement scope optimise (items avec prix x zones)...")
    scope = _get_scope(cur, args.limit)
    logger.info(
        "Scope effectif : %d paires (%d items avec prix x zones)",
        len(scope),
        len(set(p[0] for p in scope)),
    )

    if not scope:
        print(
            f"\n{YELLOW}[WARN]{RESET} Scope vide — verifier :\n"
            "  SELECT COUNT(*) FROM public.mercurials_item_map;\n"
            "  SELECT COUNT(*) FROM public.tracked_market_zones;"
        )
        conn.close()
        return 0

    if dry_run:
        print(
            f"\n{YELLOW}[DRY-RUN]{RESET} Scope calcule : {len(scope)} paires\n"
            f"  Items distincts : {len(set(p[0] for p in scope))}\n"
            f"  Zones distinctes : {len(set(p[1] for p in scope))}\n"
            f"\n  Relancer avec --apply pour l'ecriture reelle."
        )
        conn.close()
        return 0

    # Batch principal
    ok = err = empty = propagated = 0
    month = datetime.now().month

    logger.info(
        "Demarrage batch signal (apply=True) — taxo pre-chargee, 0 round-trip par paire..."
    )
    for i, (item_id, zone_id) in enumerate(scope, 1):
        try:
            # Recuperer taxo_l3 depuis le cache pre-charge (pas de requete individuelle)
            taxo = taxo_cache.get(item_id)

            signal = engine.compute_signal(item_id, zone_id, month=month, taxo_l3=taxo)

            if signal.signal_quality == "empty":
                empty += 1
                continue

            if signal.is_propagated:
                propagated += 1

            engine.persist_signal(signal, conn)
            ok += 1

            if signal.alert_level in ("CRITICAL", "WARNING"):
                logger.warning(
                    "ALERT %s | %s x %s",
                    signal.alert_level,
                    str(item_id)[:24],
                    str(zone_id)[:24],
                )

        except Exception as exc:
            err += 1
            logger.error("ERR %s x %s : %s", item_id, zone_id, exc)

        if i % args.log_every == 0:
            pct = round(i * 100 / len(scope), 1)
            logger.info(
                "[%d/%d (%s%%)] ok=%d empty=%d prop=%d err=%d",
                i,
                len(scope),
                pct,
                ok,
                empty,
                propagated,
                err,
            )

    # persist_signal() appelle deja conn.commit() par signal (signal_engine.py)

    # Probe post-batch
    logger.info("Probe post-batch...")
    post = _probe_post(cur)
    conn.close()

    # Rapport final
    print(f"\n{BOLD}=== RAPPORT BATCH SIGNAL V4 ==={RESET}")
    print(f"  Paires traitees           : {len(scope)}")
    print(f"  Signaux calcules (ok)     : {ok}")
    print(f"  Signaux propagés          : {propagated}")
    print(f"  Signaux vides             : {empty}")
    print(f"  Erreurs                   : {err}")
    print("\n  Distribution qualite :")
    for q, cnt in sorted(post["quality_distribution"].items(), key=lambda x: -x[1]):
        print(f"    {q:20}: {cnt}")

    print(f"\n  Items avec signal avant   : {pre['items_with_signal_before']}")
    print(f"  Items avec signal apres   : {post['items_with_signal_after']}")
    print(f"  Couverture dictionnaire   : {post['coverage_pct']}%")

    # Gate V4
    gate_threshold = 650
    gate_ok = post["items_with_signal_after"] >= gate_threshold
    print(f"\n{BOLD}Gate V4{RESET} (items_with_signal >= {gate_threshold}) :")
    if gate_ok:
        print(
            f"  {GREEN}[VERT]{RESET} {post['items_with_signal_after']} >= {gate_threshold} — Gate V4 valide!"
        )
    else:
        delta = gate_threshold - post["items_with_signal_after"]
        print(
            f"  {YELLOW}[PARTIEL]{RESET} {post['items_with_signal_after']} / {gate_threshold} "
            f"(delta: {delta})\n"
            f"  Actions : verifier mercurials_item_map et relancer avec --apply"
        )

    return 0 if not err else 1


if __name__ == "__main__":
    raise SystemExit(main())
