#!/usr/bin/env python3
"""
Probe TODO M7.3 — Part A (Vendors) + Part B (Hash chain).
Outputs bruts · zéro interprétation.
"""
from __future__ import annotations

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

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace(
    "postgresql+psycopg://", "postgresql://"
)
if not DATABASE_URL:
    sys.exit("DATABASE_URL manquante")

# Masquer secrets pour affichage
def _mask_url(url: str) -> str:
    if "://" not in url:
        return url
    pre, rest = url.split("://", 1)
    if "@" in rest:
        creds, hostpart = rest.rsplit("@", 1)
        user = creds.split(":")[0] if ":" in creds else "***"
        return f"{pre}://{user}:****@{hostpart}"
    return url


def run():
    print("=" * 70)
    print("PART A — VENDORS")
    print("=" * 70)

    with psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True) as conn:

        # A1
        print("\n--- A1 ---")
        for r in conn.execute("""
            SELECT current_database() AS db, current_user AS usr,
                   inet_server_addr()::TEXT AS host, inet_server_port() AS port
        """).fetchall():
            print(dict(r))
        for r in conn.execute("SELECT version_num FROM alembic_version").fetchall():
            print("alembic_version:", dict(r))

        # A2
        print("\n--- A2 ---")
        for r in conn.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name ILIKE '%vendor%'
            ORDER BY 1,2
        """).fetchall():
            print(dict(r))

        # A3
        print("\n--- A3 ---")
        for tbl in [
            "public.vendor_identities",
            "public.vendors",
            "couche_b.vendor_identities",
            "couche_b.vendors",
        ]:
            try:
                r = conn.execute(f"SELECT COUNT(*) AS n FROM {tbl}").fetchone()
                print(f"{tbl}: {r['n']}")
            except Exception as e:
                print(f"{tbl}: ERROR {e}")

    print("\n" + "=" * 70)
    print("PART B — HASH CHAIN")
    print("=" * 70)

    with psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True) as conn:

        # B1 — tables/colonnes hash
        print("\n--- B1 tables/colonnes hash ---")
        for r in conn.execute("""
            SELECT table_schema, table_name, column_name, data_type
            FROM information_schema.columns
            WHERE column_name ILIKE '%hash%'
               OR column_name ILIKE '%prev_hash%'
            ORDER BY 1,2,3
        """).fetchall():
            print(dict(r))

        # B1 — fonctions
        print("\n--- B1 fonctions ---")
        for r in conn.execute("""
            SELECT routine_schema, routine_name
            FROM information_schema.routines
            WHERE routine_name ILIKE '%hash%'
               OR routine_name ILIKE '%digest%'
               OR routine_name ILIKE '%audit%'
            ORDER BY 1,2
        """).fetchall():
            print(dict(r))

        # B1 — triggers
        print("\n--- B1 triggers ---")
        for r in conn.execute("""
            SELECT trigger_schema, trigger_name, event_object_table,
                   action_timing, event_manipulation
            FROM information_schema.triggers
            WHERE trigger_name ILIKE '%audit%'
               OR trigger_name ILIKE '%hash%'
               OR trigger_name ILIKE '%no_delete%'
            ORDER BY 1,2
        """).fetchall():
            print(dict(r))

    print("\n--- DATABASE_URL (masquée) ---")
    print(_mask_url(DATABASE_URL))
    print("=" * 70)


if __name__ == "__main__":
    run()
