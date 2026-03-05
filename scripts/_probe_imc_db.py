#!/usr/bin/env python3
"""Probe 2.1 — DB + alembic head + tables IMC existantes."""
import os
import sys

import psycopg

url = os.environ.get("DATABASE_URL")
if not url:
    print("DATABASE_URL non définie")
    sys.exit(1)
if url.startswith("postgres://"):
    url = "postgresql://" + url[9:]

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        print("=== ALEMBIC HEAD ===")
        cur.execute("SELECT version_num FROM alembic_version")
        r = cur.fetchone()
        print(r[0] if r else "VIDE")
        print()
        print("=== TABLES IMC EXISTANTES ===")
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_name LIKE %s
            ORDER BY table_name
            """,
            ("%imc%",),
        )
        rows = cur.fetchall()
        print(rows if rows else "Aucune · OK")
        print()
        print("=== IDS ALEMBIC UTILISES ===")
        cur.execute("SELECT version_num FROM alembic_version")
        print(cur.fetchall())
