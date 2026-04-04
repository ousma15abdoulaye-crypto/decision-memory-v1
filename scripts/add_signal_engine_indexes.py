#!/usr/bin/env python3
"""
add_signal_engine_indexes.py — Index fonctionnels pour signal_engine.

Cree les index CONCURRENTLY sur Railway pour accelerer les JOIN
LOWER(TRIM()) dans signal_engine.get_price_points() :
  - mercurials(LOWER(TRIM(item_canonical)))
  - mercurials_item_map(LOWER(TRIM(item_canonical)))
  - market_surveys(LOWER(TRIM(item_ref)))  [si colonne existe]

Avant  : Seq Scan 27k lignes par paire -> ~37s/paire
Apres  : Index Scan -> <1s/paire (objectif)
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dms_pg_connect import get_raw_database_url, safe_target_hint  # noqa: E402


def col_exists(conn: psycopg.Connection, table: str, column: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s AND column_name=%s
            """,
            (table, column),
        )
        return cur.fetchone() is not None


def index_exists(conn: psycopg.Connection, idx_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=%s",
            (idx_name,),
        )
        return cur.fetchone() is not None


def create_index(conn: psycopg.Connection, idx_name: str, ddl: str) -> None:
    if index_exists(conn, idx_name):
        print(f"  [SKIP] {idx_name} deja existant")
        return
    print(f"  [CREATE] {idx_name} ...")
    # CONCURRENTLY requiert autocommit=True (etabli a la connexion)
    try:
        with conn.cursor() as cur:
            cur.execute(ddl)
        print(f"  [OK] {idx_name} cree")
    except Exception as e:
        print(f"  [ERR] {idx_name}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create signal_engine performance indexes (CONCURRENTLY)."
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

    print(
        f"Connecting (autocommit=True requis pour CONCURRENTLY)... hint={safe_target_hint(db_url)}"
    )
    conn = psycopg.connect(db_url, connect_timeout=30, autocommit=True)

    print("\n=== Index fonctionnels signal_engine ===")

    # 1. mercurials.item_canonical
    if col_exists(conn, "mercurials", "item_canonical"):
        create_index(
            conn,
            "idx_mercurials_item_canonical_lower",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mercurials_item_canonical_lower "
            "ON public.mercurials (LOWER(TRIM(item_canonical)))",
        )
    else:
        print("  [SKIP] mercurials.item_canonical absent")

    # 2. mercurials_item_map.item_canonical
    if col_exists(conn, "mercurials_item_map", "item_canonical"):
        create_index(
            conn,
            "idx_mercurials_item_map_canonical_lower",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mercurials_item_map_canonical_lower "
            "ON public.mercurials_item_map (LOWER(TRIM(item_canonical)))",
        )
    else:
        print("  [SKIP] mercurials_item_map.item_canonical absent — verif colonnes...")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='mercurials_item_map'
                ORDER BY ordinal_position
                """)
            cols = [r[0] for r in cur.fetchall()]
            print(f"    mercurials_item_map colonnes: {cols}")

    # 3. zone_context_registry si present
    if col_exists(conn, "zone_context_registry", "zone_id"):
        create_index(
            conn,
            "idx_zone_context_registry_zone_item",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_zone_context_registry_zone_item "
            "ON public.zone_context_registry (zone_id, item_id)",
        )
    else:
        print("  [SKIP] zone_context_registry.zone_id absent")

    # 4. market_signals_v2 coverage index
    if col_exists(conn, "market_signals_v2", "item_id") and col_exists(
        conn, "market_signals_v2", "zone_id"
    ):
        create_index(
            conn,
            "idx_market_signals_v2_item_zone",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_signals_v2_item_zone "
            "ON public.market_signals_v2 (item_id, zone_id)",
        )
    else:
        print("  [SKIP] market_signals_v2.item_id/zone_id absent")

    # 5. market_surveys performance indexes
    for col in ["item_ref", "item_id"]:
        if col_exists(conn, "market_surveys", col):
            idx = f"idx_market_surveys_{col}_lower"
            create_index(
                conn,
                idx,
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {idx} "
                f"ON public.market_surveys (LOWER(TRIM({col})))",
            )

    print("\n=== Verification index existants sur tables cles ===")
    with conn.cursor() as cur:
        for tbl in ["mercurials", "mercurials_item_map", "market_signals_v2"]:
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
