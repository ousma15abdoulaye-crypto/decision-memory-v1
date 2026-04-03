#!/usr/bin/env python3
"""Add missing indexes for signal_engine JOIN performance."""

import os

import psycopg

RAILWAY_URL = os.environ.get(
    "RAILWAY_DATABASE_URL",
    "postgresql://postgres:VvIxShbsVuwXdqGlipWTeZjfHKTEbFHP@maglev.proxy.rlwy.net:35451/railway",
)

INDEXES = [
    # Critical: WHERE map.dict_item_id = %s
    (
        "idx_mercurials_item_map_dict_item_id",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mercurials_item_map_dict_item_id "
        "ON public.mercurials_item_map (dict_item_id)",
    ),
    # Critical: WHERE m.zone_id = %s (if no index exists)
    (
        "idx_mercurials_zone_id",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mercurials_zone_id "
        "ON public.mercurials (zone_id)",
    ),
    # market_surveys: WHERE item_id = %s AND zone_id = %s
    (
        "idx_market_surveys_item_zone",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_surveys_item_zone "
        "ON public.market_surveys (item_id, zone_id)",
    ),
    # seasonal_patterns: WHERE item_id = %s AND zone_id = %s
    (
        "idx_seasonal_patterns_item_zone",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seasonal_patterns_item_zone "
        "ON public.seasonal_patterns (item_id, zone_id)",
    ),
]


def main() -> None:
    print("Connecting to Railway (autocommit=True)...")
    conn = psycopg.connect(RAILWAY_URL, connect_timeout=30, autocommit=True)

    print("\n=== Adding missing critical indexes ===")
    with conn.cursor() as cur:
        for idx_name, ddl in INDEXES:
            cur.execute(
                "SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=%s",
                (idx_name,),
            )
            if cur.fetchone():
                print(f"  [SKIP] {idx_name} already exists")
                continue
            print(f"  [CREATE] {idx_name}...")
            try:
                cur.execute(ddl)
                print(f"  [OK] {idx_name}")
            except Exception as e:
                print(f"  [ERR] {idx_name}: {e}")

    print("\n=== Final index state ===")
    with conn.cursor() as cur:
        for tbl in ["mercurials_item_map", "mercurials", "market_surveys"]:
            cur.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename=%s ORDER BY indexname",
                (tbl,),
            )
            idx_list = [r[0] for r in cur.fetchall()]
            print(f"  {tbl}: {idx_list}")

    conn.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
