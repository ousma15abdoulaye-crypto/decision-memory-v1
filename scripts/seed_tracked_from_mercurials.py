#!/usr/bin/env python3
"""
Seed tracked_market_items depuis les données réelles mercurials + item_map.

Une seule requête SQL — items avec prix réels dans mercurials.
Idempotent : ON CONFLICT (item_id) DO NOTHING.

Usage :
  DATABASE_URL=<railway> python scripts/seed_tracked_from_mercurials.py
  RAILWAY_DATABASE_URL=<url> python scripts/seed_tracked_from_mercurials.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")
except ImportError:
    pass

db_url = os.environ.get("RAILWAY_DATABASE_URL", "") or os.environ.get(
    "DATABASE_URL", ""
)
if not db_url:
    print("ERROR: RAILWAY_DATABASE_URL / DATABASE_URL absente")
    sys.exit(1)
db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)


def main():
    with psycopg.connect(db_url, row_factory=dict_row, autocommit=True) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO public.tracked_market_items (item_id)
            SELECT DISTINCT mim.dict_item_id
            FROM mercurials m
            JOIN mercurials_item_map mim
              ON LOWER(TRIM(m.item_canonical)) =
                 LOWER(TRIM(mim.item_canonical))
            JOIN couche_b.procurement_dict_items di
              ON di.item_id = mim.dict_item_id
            WHERE m.price_avg > 0
            ON CONFLICT (item_id) DO NOTHING
        """)
        inserted = cur.rowcount

        cur.execute("SELECT COUNT(*) AS n FROM tracked_market_items")
        total = cur.fetchone()["n"]

    print(f"Inserted: {inserted} (ON CONFLICT skipped existing)")
    print(f"Total tracked_market_items: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
