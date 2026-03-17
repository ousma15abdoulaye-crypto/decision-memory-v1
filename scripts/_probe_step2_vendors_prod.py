#!/usr/bin/env python3
"""
STEP 2 — VENDORS sur DB cible (Railway prod).
Usage: DATABASE_URL_PROD=<url> python scripts/_probe_step2_vendors_prod.py
       ou DATABASE_URL=<url_railway> python scripts/_probe_step2_vendors_prod.py
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

URL = (
    os.environ.get("DATABASE_URL_PROD")
    or os.environ.get("PROD_DATABASE_URL")
    or os.environ.get("RAILWAY_DATABASE_URL")
    or os.environ.get("DATABASE_URL", "")
).replace("postgresql+psycopg://", "postgresql://")

if not URL:
    sys.exit("DATABASE_URL_PROD ou DATABASE_URL manquante")


def main():
    print("=" * 60)
    print("STEP 2 — VENDORS (DB cible)")
    print("=" * 60)

    with psycopg.connect(URL, row_factory=dict_row, autocommit=True) as conn:
        # Header obligatoire
        r = conn.execute("""
            SELECT current_database() AS db, inet_server_addr()::TEXT AS host,
                   inet_server_port() AS port, current_user AS usr
        """).fetchone()
        print(f"\ndb: {r['db']} | host: {r['host']} | port: {r['port']} | user: {r['usr']}")
        r = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        print(f"alembic_version: {r['version_num']}")

        # 2.1 Tables vendors
        print("\n--- 2.1 Tables vendors ---")
        rows = conn.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name ILIKE '%vendor%'
            ORDER BY 1,2
        """).fetchall()
        for r in rows:
            print(f"  {r['table_schema']}.{r['table_name']}")

        # Count public.vendors
        try:
            r = conn.execute("SELECT COUNT(*) AS n FROM public.vendors").fetchone()
            print(f"\n  public.vendors : {r['n']} lignes")
        except Exception as e:
            print(f"\n  public.vendors : ERROR {e}")

        # Colonnes clés public.vendors
        print("\n--- Colonnes public.vendors ---")
        try:
            rows = conn.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name='vendors'
                ORDER BY ordinal_position
            """).fetchall()
            for r in rows:
                print(f"  {r['column_name']}: {r['data_type']}")
        except Exception as e:
            print(f"  ERROR {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
