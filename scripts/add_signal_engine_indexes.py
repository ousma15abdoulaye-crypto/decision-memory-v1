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

import os

import psycopg

RAILWAY_URL = os.environ.get(
    "RAILWAY_DATABASE_URL",
    "postgresql://postgres:VvIxShbsVuwXdqGlipWTeZjfHKTEbFHP@maglev.proxy.rlwy.net:35451/railway",
)


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
    print("Connecting to Railway (autocommit=True requis pour CONCURRENTLY)...")
    conn = psycopg.connect(RAILWAY_URL, connect_timeout=30, autocommit=True)

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
