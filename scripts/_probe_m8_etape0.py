#!/usr/bin/env python3
"""Probe ÉTAPE 0 M8 — requêtes DB brutes."""
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

def _normalize_db_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url

def main():
    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("DATABASE_URL absente")
        sys.exit(1)
    if "railway" in db.lower():
        print("CONTRACT-02: railway interdit")
        sys.exit(1)
    conn = psycopg.connect(_normalize_db_url(db), row_factory=dict_row)
    cur = conn.cursor()

    print("=== TABLES CHECK ===")
    cur.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_name IN (
          'procurement_dict_items','units','geo_master',
          'vendors','cases','users','dict_collision_log',
          'market_surveys','market_signals',
          'zone_context_registry','seasonal_patterns'
        ) ORDER BY table_schema, table_name
    """)
    for r in cur.fetchall():
        print(r)

    print("\n=== dict_collision_log COLUMNS ===")
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'dict_collision_log'
        ORDER BY ordinal_position
    """)
    for r in cur.fetchall():
        print(r)

    print("\n=== dict_collision_log RESOLUTION (status si existe) ===")
    cur.execute("""
        SELECT resolution, COUNT(*)
        FROM dict_collision_log
        GROUP BY resolution ORDER BY resolution
    """)
    for r in cur.fetchall():
        print(r)

    print("\n=== ROUTINES fn_reject_mutation etc ===")
    cur.execute("""
        SELECT routine_name, routine_schema
        FROM information_schema.routines
        WHERE routine_name IN (
          'fn_reject_mutation','fnrejectmutation',
          'fn_sre_append_only','fn_append_only'
        )
    """)
    for r in cur.fetchall():
        print(r)

    print("\n=== geo_master colonnes + level 1,2 ===")
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name='geo_master'
        ORDER BY ordinal_position
    """)
    cols_gm = [r["column_name"] for r in cur.fetchall()]
    print("Colonnes geo_master:", cols_gm)
    # Utiliser colonnes existantes (id, name, level si présents)
    sel = ", ".join(c for c in cols_gm if c in ("id", "name", "level", "code", "type"))
    if not sel:
        sel = "id, name"
    cur.execute(f"""
        SELECT {sel} FROM geo_master
        WHERE level IN (1,2) OR level IS NULL
        ORDER BY level NULLS LAST
        LIMIT 25
    """)
    for r in cur.fetchall():
        print(dict(r))
    for r in cur.fetchall():
        print(r)

    print("\n=== pg_extensions ===")
    cur.execute("""
        SELECT extname FROM pg_extension
        WHERE extname IN ('pgcrypto','pg_trgm')
    """)
    for r in cur.fetchall():
        print(r)

    print("\n=== procurement_dict_items TOUTES colonnes ===")
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema='couche_b' AND table_name='procurement_dict_items'
        ORDER BY ordinal_position
    """)
    for r in cur.fetchall():
        print(r)

    print("\n=== geo_master id type + sample ids ===")
    cur.execute("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema='public' AND table_name='geo_master'
          AND column_name='id'
    """)
    r = cur.fetchone()
    print("geo_master.id type:", r["data_type"] if r else "N/A")
    cur.execute("SELECT id, name, level FROM geo_master ORDER BY level, name LIMIT 15")
    for r in cur.fetchall():
        print(r)

    conn.close()
    print("\n=== PROBE OK ===")

if __name__ == "__main__":
    main()
