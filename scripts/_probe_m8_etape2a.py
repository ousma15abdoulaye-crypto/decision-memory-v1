#!/usr/bin/env python3
"""Probe ÉTAPE 2A M8 — types FK (id columns)."""
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

def main():
    db = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db, row_factory=dict_row)
    cur = conn.cursor()

    cur.execute("""
        SELECT table_schema, table_name, column_name, data_type,
               character_maximum_length
        FROM information_schema.columns
        WHERE table_name IN (
          'vendors','units','cases','users',
          'geo_master','procurement_dict_items'
        )
          AND column_name = 'id'
        ORDER BY table_schema, table_name
    """)
    print("table_schema | table_name | column_name | data_type | character_maximum_length")
    print("-" * 75)
    for r in cur.fetchall():
        print(f"{r['table_schema']:12} | {r['table_name']:24} | {r['column_name']:12} | {r['data_type']:12} | {r['character_maximum_length']}")
    conn.close()

if __name__ == "__main__":
    main()
