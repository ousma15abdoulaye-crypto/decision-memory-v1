#!/usr/bin/env python3
"""Diagnostic types mercurials / mercurials_item_map — Railway."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass
import psycopg

db = os.environ.get("RAILWAY_DATABASE_URL", "").replace(
    "postgresql+psycopg://", "postgresql://"
)
if not db:
    print("RAILWAY_DATABASE_URL absente")
    exit(1)

with psycopg.connect(db, autocommit=True) as conn:
    cur = conn.cursor()

    print("=== 1. Types réels des colonnes concernées ===")
    cur.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE (table_name = 'mercurials'
               AND column_name IN ('item_id','item_canonical','item_code'))
           OR (table_name = 'mercurials_item_map'
               AND column_name IN ('item_id','item_canonical'))
        ORDER BY table_name, column_name
    """)
    for r in cur.fetchall():
        print(r)

    print("\n=== 2a. Une ligne mercurials ===")
    cur.execute("""
        SELECT item_canonical, item_id,
               pg_typeof(item_id)::text AS type_reel
        FROM mercurials
        LIMIT 1
    """)
    for r in cur.fetchall():
        print(r)

    print("\n=== 2b. Une ligne mercurials_item_map ===")
    cur.execute("""
        SELECT item_canonical, dict_item_id,
               pg_typeof(dict_item_id)::text AS type_reel
        FROM mercurials_item_map
        LIMIT 1
    """)
    for r in cur.fetchall():
        print(r)
