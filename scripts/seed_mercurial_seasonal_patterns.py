#!/usr/bin/env python3
"""
Calcule et insère des seasonal_patterns
depuis les données mercurials réelles.

LIMITATION DOCUMENTÉE :
  mercurials ne contient pas de granularité mensuelle.
  Les historical_deviation_pct insérés sont 0.0.
  Ces patterns servent à documenter la couverture
  taxo_l3 × zone_id dans le système.
  Les ajustements réels de prix viennent de
  zone_context_registry.structural_markup.
  Une révision avec données mensuelles (IMC INSTAT
  ou surveys terrain) est nécessaire pour des
  historical_deviation_pct non nuls.

Idempotent via ON CONFLICT DO UPDATE.

Usage :
  python scripts/seed_mercurial_seasonal_patterns.py
  python scripts/seed_mercurial_seasonal_patterns.py \
    --dry-run
"""

import os
import sys
import logging
import argparse
import statistics
from collections import defaultdict
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

COMPUTATION_VERSION = "v1.1_mercurials"
MIN_OBSERVATIONS = 3  # minimum par (taxo_l3, zone, month)
# Données annuelles mercurials → mois de référence = 6 (milieu année)
REF_MONTH = 6


def check_env() -> str:
    db = (
        os.environ.get("RAILWAY_DATABASE_URL", "") or os.environ.get("DATABASE_URL", "")
    ).replace("postgresql+psycopg://", "postgresql://")
    if not db:
        raise SystemExit("DATABASE_URL absent")
    if not any(k in db for k in ["rlwy", "maglev", "railway"]):
        ans = input("DB ne semble pas Railway. [oui/NON]: ")
        if ans.lower() != "oui":
            raise SystemExit("Annulé")
    return db


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = psycopg.connect(check_env(), row_factory=dict_row)
    cur = conn.cursor()

    # Charger les prix avec year et taxo_l3 (jointure LOWER/TRIM comme signal_engine)
    log.info("Chargement des prix mercurials...")
    cur.execute("""
        SELECT
            di.taxo_l3,
            di.taxo_l1,
            di.taxo_l2,
            m.zone_id,
            m.year,
            m.price_avg
        FROM mercurials m
        JOIN mercurials_item_map mim
          ON LOWER(TRIM(m.item_canonical)) =
             LOWER(TRIM(mim.item_canonical))
        JOIN couche_b.procurement_dict_items di
          ON di.item_id = mim.dict_item_id
        WHERE m.price_avg > 0
          AND di.taxo_l3 IS NOT NULL
          AND m.zone_id IS NOT NULL
        ORDER BY di.taxo_l3, m.zone_id, m.year
    """)
    rows = cur.fetchall()
    log.info("Lignes chargées : %d", len(rows))

    if not rows:
        log.error("0 lignes — vérifier mercurials_item_map")
        sys.exit(1)

    # Grouper par (zone_id, taxo_l3) — données annuelles → month = REF_MONTH
    groups: dict = defaultdict(list)
    meta: dict = {}
    for r in rows:
        key = (r["zone_id"], r["taxo_l3"])
        groups[key].append(
            {
                "year": r["year"],
                "price_avg": float(r["price_avg"]),
            }
        )
        if key not in meta:
            meta[key] = {
                "taxo_l1": r["taxo_l1"],
                "taxo_l2": r["taxo_l2"],
            }

    patterns_to_insert = []

    for (zone_id, taxo_l3), prix_list in groups.items():
        if len(prix_list) < MIN_OBSERVATIONS:
            continue

        prices = [p["price_avg"] for p in prix_list]
        mean = statistics.mean(prices)
        if mean == 0:
            continue

        # Données annuelles — pas de granularité mensuelle dans mercurials.
        # Déviation saisonnière = 0.
        # Les ajustements viendront de zone_context_registry
        # (structural_markup) et non de seasonal_patterns pour ces données.
        historical_deviation_pct = 0.0
        confidence = min(0.95, 0.50 + len(prix_list) * 0.05)
        me = meta[(zone_id, taxo_l3)]

        patterns_to_insert.append(
            {
                "zone_id": zone_id,
                "taxo_l1": me["taxo_l1"],
                "taxo_l2": me["taxo_l2"],
                "taxo_l3": taxo_l3,
                "month": REF_MONTH,
                "historical_deviation_pct": historical_deviation_pct,
                "years_observed": len(prix_list),
                "confidence": round(confidence, 2),
                "computation_version": COMPUTATION_VERSION,
            }
        )

    log.info("Patterns calculés : %d", len(patterns_to_insert))

    if args.dry_run:
        for p in patterns_to_insert[:5]:
            log.info("  DRY: %s", p)
        conn.close()
        sys.exit(0)

    # Insérer avec savepoint par pattern (évite transaction abort)
    ok = err = 0
    for p in patterns_to_insert:
        try:
            cur.execute("SAVEPOINT sp_pattern")
            cur.execute(
                """
                INSERT INTO public.seasonal_patterns (
                    zone_id, taxo_l1, taxo_l2, taxo_l3,
                    month, historical_deviation_pct, years_observed,
                    confidence, crisis_years_excluded, baseline_method,
                    data_source, computation_version, last_computed
                ) VALUES (
                    %(zone_id)s, %(taxo_l1)s, %(taxo_l2)s, %(taxo_l3)s,
                    %(month)s, %(historical_deviation_pct)s, %(years_observed)s,
                    %(confidence)s, 0, 'mean', 'mercuriale_2023_2026',
                    %(computation_version)s, CURRENT_DATE
                )
                ON CONFLICT (zone_id, taxo_l3, month, computation_version)
                DO UPDATE SET
                    historical_deviation_pct = EXCLUDED.historical_deviation_pct,
                    years_observed = EXCLUDED.years_observed,
                    confidence = EXCLUDED.confidence,
                    last_computed = CURRENT_DATE
            """,
                p,
            )
            cur.execute("RELEASE SAVEPOINT sp_pattern")
            ok += 1
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp_pattern")
            log.error("ERR %s: %s", p, e)
            err += 1

    conn.commit()
    log.info("DONE ok=%d err=%d", ok, err)

    # Vérifier
    cur.execute("""
        SELECT computation_version, COUNT(*) AS n
        FROM seasonal_patterns
        GROUP BY computation_version
        ORDER BY computation_version
    """)
    for r in cur.fetchall():
        log.info("  patterns %s : %d", r["computation_version"], r["n"])

    conn.close()
    sys.exit(1 if err > 0 else 0)


if __name__ == "__main__":
    main()
