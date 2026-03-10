#!/usr/bin/env python3
"""
Seed seasonal_patterns depuis indices INSTAT Mali.

Source : public.imc_entries
  period_year INT, period_month INT,
  category_raw TEXT, index_value NUMERIC

computation_version = 'v1.0_instat'
confidence = 0.95 (source officielle nationale)
taxo_l1 = 'Materiaux de construction'

Usage : python scripts/seed_instat_seasonal_patterns.py
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

COMPUTATION_VERSION = "v1.0_instat"
DATA_SOURCE = "instat_mali_2018_2026"
TAXO_L1 = "Materiaux de construction"
CONFIDENCE = 0.95


def env() -> str:
    u = os.environ.get("DATABASE_URL", "")
    if not u:
        raise SystemExit("DATABASE_URL absent")
    return u.replace("postgresql+psycopg://", "postgresql://")


def main():
    conn = psycopg.connect(env(), row_factory=dict_row)
    cur = conn.cursor()

    # Verifier que imc_entries existe
    cur.execute("""
        SELECT COUNT(*) AS n FROM information_schema.tables
        WHERE table_name = 'imc_entries'
    """)
    if cur.fetchone()["n"] == 0:
        print("WARN : imc_entries absente -- skip INSTAT")
        conn.close()
        sys.exit(0)

    cur.execute("""
        SELECT category_raw, period_year, period_month, index_value
        FROM public.imc_entries
        WHERE index_value > 0
          AND category_raw IS NOT NULL
          AND category_raw NOT LIKE '%main%'
        ORDER BY period_year, period_month
    """)
    rows = cur.fetchall()
    print(f"Lignes imc_entries : {len(rows)}")

    if len(rows) < 12:
        print("WARN : moins de 12 lignes INSTAT")
        conn.close()
        sys.exit(0)

    # Zones trackees
    cur.execute("""
        SELECT tmz.zone_id, gm.name AS zone_name
        FROM public.tracked_market_zones tmz
        JOIN public.geo_master gm ON gm.id = tmz.zone_id
        ORDER BY gm.name
    """)
    zones = cur.fetchall()
    if not zones:
        print("WARN : aucune zone trackee")
        conn.close()
        sys.exit(0)
    print(f"Zones trackees : {len(zones)}")

    # Aggreger par (category_raw, month)
    groups: dict = defaultdict(list)
    for r in rows:
        groups[(r["category_raw"], r["period_month"])].append(float(r["index_value"]))

    # Moyenne annuelle par categorie
    ann: dict = defaultdict(list)
    for (cat, m), vals in groups.items():
        ann[cat].extend(vals)
    ann_mean = {k: statistics.mean(v) for k, v in ann.items() if v}

    ins = skip = 0
    for zone in zones:
        zone_id = zone["zone_id"]
        for (cat, month), vals in groups.items():
            if len(vals) < 2:
                skip += 1
                continue
            am = ann_mean.get(cat)
            if not am or am == 0:
                skip += 1
                continue

            dev = ((statistics.mean(vals) / am) - 1) * 100
            yrs = len(vals) // 12 + 1

            try:
                cur.execute(
                    """
                    INSERT INTO public.seasonal_patterns (
                        zone_id, taxo_l1, taxo_l2,
                        taxo_l3, item_id, month,
                        historical_deviation_pct,
                        confidence, years_observed,
                        crisis_years_excluded,
                        baseline_method, data_source,
                        computation_version, last_computed
                    ) VALUES (
                        %s,%s,NULL,%s,NULL,%s,
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
                        zone_id,
                        TAXO_L1,
                        cat,
                        month,
                        round(dev, 3),
                        CONFIDENCE,
                        yrs,
                        DATA_SOURCE,
                        COMPUTATION_VERSION,
                    ),
                )
                ins += 1
            except Exception as e:
                print(f"ERR {zone_id} {cat} m{month}: {e}")
                skip += 1

    conn.commit()
    print(f"INSTAT seasonal_patterns: ins={ins} skip={skip} zones={len(zones)}")
    conn.close()


if __name__ == "__main__":
    main()
