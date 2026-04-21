#!/usr/bin/env python3
"""
Import de données terrain dans market_surveys.

Format CSV attendu :
  item_id,zone_id,price_per_unit,date_surveyed,source_ref

Validation :
  item_id   → doit exister dans dict_items actif
  zone_id   → doit exister dans tracked_market_zones
  price     → > 0
  date      → <= today

Usage :
  python scripts/import_market_surveys.py \
    --file data/surveys_import.csv \
    --dry-run
  python scripts/import_market_surveys.py \
    --file data/surveys_import.csv
"""

import os
import sys
import csv
import logging
import argparse
from datetime import date, datetime
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


def check_env() -> str:
    db = (
        os.environ.get("RAILWAY_DATABASE_URL", "") or os.environ.get("DATABASE_URL", "")
    ).replace("postgresql+psycopg://", "postgresql://")
    if not db:
        raise SystemExit("DATABASE_URL absent")
    return db


def validate_row(
    row: dict,
    valid_items: set,
    valid_zones: set,
) -> tuple[bool, str]:
    # Normaliser avant comparaison
    item_id = (row.get("item_id") or "").strip()
    zone_id = (row.get("zone_id") or "").strip()

    if not item_id or item_id not in valid_items:
        return False, f"item_id inconnu: '{item_id}'"
    if not zone_id or zone_id not in valid_zones:
        return False, f"zone_id inconnu: '{zone_id}'"

    # Normaliser aussi dans le row pour l'INSERT
    row["item_id"] = item_id
    row["zone_id"] = zone_id

    try:
        price = float(row.get("price_per_unit", 0))
        if price <= 0:
            return False, f"price <= 0: {price}"
    except (ValueError, TypeError):
        return False, "price invalide"

    try:
        d = datetime.strptime(
            (row.get("date_surveyed") or "").strip(), "%Y-%m-%d"
        ).date()
        if d > date.today():
            return False, f"date future: {d}"
        row["date_surveyed"] = str(d)
    except (ValueError, KeyError):
        return False, "date invalide"

    return True, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = psycopg.connect(check_env(), row_factory=dict_row)
    cur = conn.cursor()

    cur.execute("""
        SELECT item_id FROM couche_b.procurement_dict_items
        WHERE active = TRUE
    """)
    valid_items = {r["item_id"] for r in cur.fetchall()}

    cur.execute("SELECT zone_id FROM tracked_market_zones")
    valid_zones = {r["zone_id"] for r in cur.fetchall()}

    log.info("Référentiels : %d items, %d zones", len(valid_items), len(valid_zones))

    with open(args.file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    log.info("Lignes CSV : %d", len(rows))

    ok = err = skip = 0
    for row in rows:
        valid, reason = validate_row(row, valid_items, valid_zones)
        if not valid:
            log.warning("SKIP: %s — %s", row, reason)
            skip += 1
            continue

        if args.dry_run:
            log.info("DRY: %s", row)
            ok += 1
            continue

        try:
            cur.execute("SAVEPOINT sp_survey")
            price = float(row["price_per_unit"])
            cur.execute(
                """
                INSERT INTO public.market_surveys (
                    item_id,
                    zone_id,
                    price_quoted,
                    quantity_surveyed,
                    supplier_raw,
                    date_surveyed,
                    validation_status,
                    notes
                ) VALUES (
                    %(item_id)s,
                    %(zone_id)s,
                    %(price)s,
                    1.0,
                    'import',
                    %(date_surveyed)s,
                    'validated',
                    %(source_ref)s
                )
            """,
                {
                    "item_id": row["item_id"],
                    "zone_id": row["zone_id"],
                    "price": price,
                    "date_surveyed": row["date_surveyed"],
                    "source_ref": row.get("source_ref"),
                },
            )
            cur.execute("RELEASE SAVEPOINT sp_survey")
            ok += 1
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp_survey")
            log.error("ERR: %s — %s", row, e)
            err += 1

    if not args.dry_run:
        conn.commit()

    log.info("DONE ok=%d skip=%d err=%d", ok, skip, err)

    cur.execute("SELECT COUNT(*) AS n FROM market_surveys")
    log.info("market_surveys total : %d", cur.fetchone()["n"])
    conn.close()
    sys.exit(1 if err > 0 else 0)


if __name__ == "__main__":
    main()
