#!/usr/bin/env python3
"""Add missing indexes for signal_engine JOIN performance."""

import argparse
import os
import sys
from pathlib import Path

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dms_pg_connect import get_raw_database_url, safe_target_hint  # noqa: E402

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
    parser = argparse.ArgumentParser(
        description="Add missing indexes for signal_engine JOIN performance."
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="PostgreSQL URL (sinon RAILWAY_DATABASE_URL / DATABASE_URL)",
    )
    args = parser.parse_args()
    try:
        db_url = get_raw_database_url(args.db_url)
    except ValueError as e:
        raw = (
            os.environ.get("RAILWAY_DATABASE_URL")
            or os.environ.get("DATABASE_URL")
            or ""
        )
        hint = safe_target_hint(raw) if raw.strip() else "(env non configure)"
        print(
            f"[ERR] {e}\n"
            "  Definir RAILWAY_DATABASE_URL ou DATABASE_URL, ou passer --db-url.\n"
            f"  Cible (hint) : {hint}",
            file=sys.stderr,
        )
        raise SystemExit(2) from e

    print(f"Connecting (autocommit=True)... hint={safe_target_hint(db_url)}")
    conn = psycopg.connect(db_url, connect_timeout=30, autocommit=True)

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
