#!/usr/bin/env python3
"""
Seed tracked_market_zones sur Railway depuis zones avec données mercurials.

Option A — scope compute = 0 car tracked_market_zones vide.
Ce script peuple les zones depuis mercurials.zone_id (zones avec prix réels).

Usage :
  RAILWAY_DATABASE_URL=<url> python scripts/seed_tracked_zones_railway.py
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


def main() -> int:
    with psycopg.connect(db_url, row_factory=dict_row, autocommit=True) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO public.tracked_market_zones (zone_id, priority, notes)
            SELECT DISTINCT m.zone_id, 'standard',
                   'Zone avec mercurials — seed Option A'
            FROM mercurials m
            JOIN public.geo_master g ON g.id = m.zone_id
            WHERE m.zone_id IS NOT NULL
              AND m.price_avg > 0
            ON CONFLICT (zone_id) DO NOTHING
        """)
        inserted = cur.rowcount

        cur.execute("SELECT COUNT(*) AS n FROM tracked_market_zones")
        total = cur.fetchone()["n"]

    print(f"Inserted: {inserted} zones")
    print(f"Total tracked_market_zones: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
