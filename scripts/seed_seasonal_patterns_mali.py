#!/usr/bin/env python3
"""
Seed seasonal_patterns depuis mercuriales 2023-2026.
Jointure via mercurials_item_map (item_canonical -> dict_item_id).
data_source = 'mercuriale_2023_2026'
computation_version = 'v1.0'

Usage : python scripts/seed_seasonal_patterns_mali.py
"""

import os
import statistics
import sys
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

COMPUTATION_VERSION = "v1.0"
DATA_SOURCE = "mercuriale_2023_2026"
MIN_LIGNES = 50


def env() -> str:
    u = os.environ.get("DATABASE_URL", "")
    if not u:
        raise SystemExit("DATABASE_URL absent")
    return u.replace("postgresql+psycopg://", "postgresql://")


def main():
    conn = psycopg.connect(env(), row_factory=dict_row)
    cur = conn.cursor()

    # Verifier que mercurials_item_map existe
    cur.execute("""
        SELECT COUNT(*) AS n FROM information_schema.tables
        WHERE table_name = 'mercurials_item_map'
    """)
    if cur.fetchone()["n"] == 0:
        print("WARN : mercurials_item_map absente (table Railway uniquement)")
        print("Seed seasonal_patterns mercuriales ignore localement.")
        conn.close()
        sys.exit(0)

    # Charger mercuriales via mapping
    cur.execute("""
        SELECT m.zone_id,
               di.taxo_l3,
               di.taxo_l1,
               di.taxo_l2,
               di.item_id,
               m.year,
               m.price_avg AS prix
        FROM mercurials m
        JOIN public.mercurials_item_map map
          ON map.item_canonical = m.item_canonical
        JOIN couche_b.procurement_dict_items di
          ON di.item_id = map.dict_item_id
        WHERE m.price_avg > 0
          AND di.taxo_l3 IS NOT NULL
          AND m.year >= EXTRACT(YEAR FROM CURRENT_DATE)::int - 4
    """)
    rows = cur.fetchall()
    print(f"Lignes mercuriales joignables : {len(rows)}")

    if len(rows) < MIN_LIGNES:
        print(f"WARN : {len(rows)} < {MIN_LIGNES} -- seeds limites")

    # Aggreger par (zone, taxo_l3, annee) -> simuler mois = 6 (milieu annee)
    groups: dict = defaultdict(list)
    meta: dict = {}
    for r in rows:
        # Mercuriales annuelles -> on distribue sur mois 6 (reference annuelle)
        k = (r["zone_id"], r["taxo_l3"], 6)
        groups[k].append(float(r["prix"]))
        meta[k] = {
            "taxo_l1": r["taxo_l1"],
            "taxo_l2": r["taxo_l2"],
            "item_id": r["item_id"],
        }

    # Moyenne annuelle par (zone, taxo_l3)
    ann: dict = defaultdict(list)
    for (z, t, m), prices in groups.items():
        ann[(z, t)].extend(prices)
    ann_mean = {k: statistics.mean(v) for k, v in ann.items() if v}

    ins = skip = 0
    for (z, t, m), prices in groups.items():
        if len(prices) < 2:
            skip += 1
            continue
        am = ann_mean.get((z, t))
        if not am or am == 0:
            skip += 1
            continue

        dev = ((statistics.mean(prices) / am) - 1) * 100
        conf = round(min(1.0, len(prices) / 4.0), 2)
        me = meta[(z, t, m)]

        try:
            cur.execute(
                """
                INSERT INTO public.seasonal_patterns (
                    zone_id, taxo_l1, taxo_l2, taxo_l3,
                    item_id, month,
                    historical_deviation_pct,
                    confidence, years_observed,
                    crisis_years_excluded,
                    baseline_method, data_source,
                    computation_version, last_computed
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,
                    %s,%s,%s,0,
                    'mean',%s,%s,CURRENT_DATE
                )
                ON CONFLICT (zone_id, taxo_l3, month, computation_version)
                DO UPDATE SET
                    historical_deviation_pct =
                        EXCLUDED.historical_deviation_pct,
                    confidence     = EXCLUDED.confidence,
                    years_observed = EXCLUDED.years_observed,
                    last_computed  = CURRENT_DATE
                """,
                (
                    z,
                    me["taxo_l1"],
                    me["taxo_l2"],
                    t,
                    me["item_id"],
                    m,
                    round(dev, 3),
                    conf,
                    len(prices),
                    DATA_SOURCE,
                    COMPUTATION_VERSION,
                ),
            )
            ins += 1
        except Exception as e:
            print(f"ERR {z} {t} m{m}: {e}")
            skip += 1

    conn.commit()
    print(f"seasonal_patterns mercuriales: ins={ins} skip={skip}")
    conn.close()


if __name__ == "__main__":
    main()
