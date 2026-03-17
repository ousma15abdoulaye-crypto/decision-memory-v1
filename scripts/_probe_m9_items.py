#!/usr/bin/env python3
"""Probe public.items structure."""
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

db = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(db, row_factory=dict_row, autocommit=True)
cur = conn.cursor()

print("=== public.items colonnes ===")
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='items' AND table_schema='public' ORDER BY ordinal_position")
for r in cur.fetchall():
    print(f"  {r['column_name']:30} {r['data_type']}")

cur.execute("SELECT COUNT(*) AS n FROM public.items")
print(f"  Lignes: {cur.fetchone()['n']}")

print("\n=== public.items sample (3) ===")
cur.execute("SELECT * FROM public.items LIMIT 3")
for r in cur.fetchall():
    print(f"  {dict(r)}")

print("\n=== public.dict_items colonnes ===")
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='dict_items' AND table_schema='public' ORDER BY ordinal_position")
for r in cur.fetchall():
    print(f"  {r['column_name']:30} {r['data_type']}")

# Peut-on joindre mercurials -> items -> market_signals ?
print("\n=== Jointure possible mercurials -> items ? ===")
cur.execute("""
    SELECT m.column_name AS merc_col, m.data_type AS merc_type,
           i.column_name AS items_col, i.data_type AS items_type
    FROM information_schema.columns m
    JOIN information_schema.columns i
      ON m.data_type = i.data_type
    WHERE m.table_name = 'mercurials'
      AND i.table_name = 'items'
      AND i.table_schema = 'public'
      AND m.column_name NOT IN ('id','created_at','updated_at')
      AND i.column_name NOT IN ('created_at','updated_at')
    ORDER BY m.column_name, i.column_name
""")
for r in cur.fetchall():
    print(f"  merc.{r['merc_col']}({r['merc_type']}) <-> items.{r['items_col']}({r['items_type']})")

conn.close()
print("\n=== PROBE ITEMS COMPLETE ===")
