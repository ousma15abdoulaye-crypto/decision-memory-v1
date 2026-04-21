"""
SEED — DETTE-2 M11
Initialise market_surveys avec des donnees proxy
issues des mercurials agreges par annee (mercurials a year, pas de mois).

Strategie :
  Agreger mercurials par (zone_id, dict_item_id, year)
  pour les zones qui ont un context FEWS.
  survey_date = 1er juin de l'annee.
  supplier_raw = 'mercurials_proxy' (NOT NULL).
  collection_method = 'phone' (CHECK).

Regle rollback : conn.rollback() sur tout except.
Idempotence : skip si (zone_id, item_id, date_surveyed, supplier_raw) existe.

Usage : DATABASE_URL=<railway> DMS_ALLOW_RAILWAY=1 \
        python scripts/seed_market_surveys_init.py
"""

import os
import sys
from datetime import date
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row


def main():
    db_url = os.environ.get("RAILWAY_DATABASE_URL", "") or os.environ.get(
        "DATABASE_URL", ""
    )
    if not db_url:
        sys.exit("STOP — DATABASE_URL absente")
    if "railway" in db_url.lower() and os.environ.get("DMS_ALLOW_RAILWAY", "0") != "1":
        sys.exit("STOP — CONTRACT-02")
    if "://" in db_url:
        scheme_part, rest = db_url.split("://", 1)
        base_scheme = scheme_part.split("+")[0]
        db_url = f"{base_scheme}://{rest}"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    url = db_url

    ok = skip = err = 0

    with psycopg.connect(url, row_factory=dict_row) as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                m.zone_id,
                mim.dict_item_id AS item_id,
                m.year,
                ROUND(AVG(m.price_avg)::numeric, 2) AS price_quoted,
                COUNT(*) AS n_obs
            FROM mercurials m
            JOIN mercurials_item_map mim
              ON LOWER(TRIM(mim.item_canonical)) = LOWER(TRIM(m.item_canonical))
            JOIN zone_context_registry zcr ON zcr.zone_id = m.zone_id AND zcr.valid_until IS NULL
            WHERE m.zone_id IS NOT NULL
              AND m.price_avg > 0
            GROUP BY m.zone_id, mim.dict_item_id, m.year
            HAVING COUNT(*) >= 2
            ORDER BY m.zone_id, mim.dict_item_id, m.year
        """)
        surveys = cur.fetchall()

        print(f"INFO — {len(surveys)} surveys proxy calcules")

        for row in surveys:
            survey_date = date(int(row["year"]), 6, 1)
            cur.execute(
                """
                SELECT 1 FROM market_surveys
                WHERE zone_id = %s AND item_id = %s AND date_surveyed = %s
                """,
                (row["zone_id"], row["item_id"], survey_date),
            )
            if cur.fetchone():
                skip += 1
                continue

            try:
                cur.execute("SAVEPOINT sp_survey")
                cur.execute(
                    """
                    INSERT INTO market_surveys
                        (zone_id, item_id, date_surveyed, price_quoted,
                         quantity_surveyed, supplier_raw, collection_method,
                         validation_status)
                    VALUES (%s, %s, %s, %s, 1.0, 'mercurials_proxy', 'phone', 'validated')
                    """,
                    (row["zone_id"], row["item_id"], survey_date, row["price_quoted"]),
                )
                cur.execute("RELEASE SAVEPOINT sp_survey")
                ok += 1
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sp_survey")
                print(f"ERR ({row['zone_id']}, {row['item_id']}, {survey_date}) — {e}")
                err += 1

        conn.commit()
        print("INFO — commit final")

    print(f"\nRESULTAT ok={ok} skip={skip} err={err}")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
