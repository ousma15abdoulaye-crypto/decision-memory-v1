"""
SEED — DETTE-4 M11
Complete seasonal_patterns pour les zones nouvellement
mappees en ETAPE 1 et 2 (14 zones + Menaka).

Mercurials a year + price_avg (pas de granularite mensuelle).
Pour zones sans seasonal_patterns : insertion month=6,
historical_deviation_pct=0 (donnees annuelles).

ON CONFLICT DO UPDATE — idempotent.

Regle rollback : savepoint par batch (zone_id, taxo_l3).

Usage : DATABASE_URL=<railway> DMS_ALLOW_RAILWAY=1 \
        python scripts/seed_seasonal_patterns_complete.py
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

MIN_OBS = 2
FORMULA_VER = "v1.1_mercurials"
DATA_SOURCE = "mercuriale_2023_2026"
REF_MONTH = 6


def main():
    db_url = os.environ.get("RAILWAY_DATABASE_URL", "") or os.environ.get(
        "DATABASE_URL", ""
    )
    if not db_url:
        sys.exit("STOP — DATABASE_URL absente")
    if "railway" in db_url.lower() and os.environ.get("DMS_ALLOW_RAILWAY", "0") != "1":
        sys.exit("STOP — CONTRACT-02")
    url = db_url.replace("postgresql+psycopg://", "postgresql://")

    ok = skip = err = 0

    with psycopg.connect(url, row_factory=dict_row) as conn:
        cur = conn.cursor()

        # Candidats : (zone_id, taxo_l3) dans zones mappees mais absents de seasonal_patterns
        cur.execute(
            """
            SELECT
                m.zone_id,
                di.taxo_l3,
                di.taxo_l1,
                di.taxo_l2,
                di.item_id,
                AVG(m.price_avg) AS avg_price,
                COUNT(*) AS n_obs
            FROM mercurials m
            JOIN mercurials_item_map mim
              ON LOWER(TRIM(mim.item_canonical)) = LOWER(TRIM(m.item_canonical))
            JOIN couche_b.procurement_dict_items di
              ON di.item_id = mim.dict_item_id
            WHERE m.zone_id IN (
                SELECT zcr.zone_id FROM zone_context_registry zcr
                WHERE zcr.valid_until IS NULL
                AND zcr.zone_id NOT IN (
                    SELECT DISTINCT zone_id FROM seasonal_patterns
                )
            )
            AND m.zone_id IS NOT NULL
            AND di.taxo_l3 IS NOT NULL
            AND m.price_avg > 0
            GROUP BY m.zone_id, di.taxo_l3, di.taxo_l1, di.taxo_l2, di.item_id
            HAVING COUNT(*) >= %s
        """,
            (MIN_OBS,),
        )
        candidates = cur.fetchall()

        if not candidates:
            print("INFO — Aucun nouveau pattern a calculer")
            print("RESULTAT ok=0 skip=0 err=0")
            sys.exit(0)

        print(f"INFO — {len(candidates)} groupes (zone_id, taxo_l3) candidats")

        for row in candidates:
            zone_id = row["zone_id"]
            taxo_l3 = row["taxo_l3"]
            taxo_l1 = row["taxo_l1"] or "unknown"
            taxo_l2 = row["taxo_l2"] or "unknown"
            item_id = row["item_id"]
            avg_price = float(row["avg_price"])
            n_obs = row["n_obs"]

            if avg_price <= 0:
                skip += 1
                continue

            try:
                cur.execute("SAVEPOINT sp_pattern")
                cur.execute(
                    """
                    INSERT INTO seasonal_patterns
                        (zone_id, taxo_l1, taxo_l2, taxo_l3, item_id,
                         month, historical_deviation_pct, years_observed,
                         baseline_method, data_source, computation_version, last_computed)
                    VALUES (%s, %s, %s, %s, %s, %s, 0.0, %s, 'mean', %s, %s, CURRENT_DATE)
                    ON CONFLICT (zone_id, taxo_l3, month, computation_version)
                    DO UPDATE SET
                        historical_deviation_pct = EXCLUDED.historical_deviation_pct,
                        years_observed = EXCLUDED.years_observed,
                        last_computed = CURRENT_DATE
                    """,
                    (
                        zone_id,
                        taxo_l1,
                        taxo_l2,
                        taxo_l3,
                        item_id,
                        REF_MONTH,
                        n_obs,
                        DATA_SOURCE,
                        FORMULA_VER,
                    ),
                )
                cur.execute("RELEASE SAVEPOINT sp_pattern")
                conn.commit()
                print(f"OK   {zone_id:25} {taxo_l3:20} n={n_obs} mean={avg_price:,.0f}")
                ok += 1
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sp_pattern")
                conn.rollback()
                print(f"ERR  ({zone_id}, {taxo_l3}) — {e}")
                err += 1

    print(f"\nRESULTAT ok={ok} skip={skip} err={err}")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
