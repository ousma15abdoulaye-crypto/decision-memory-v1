#!/usr/bin/env python3
"""Probe complementaire M9 — A through F."""
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

def q(label, sql, params=None):
    print(f"\n=== {label} ===")
    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
        if not rows:
            print("  (vide)")
        for r in rows:
            print("  " + " | ".join(f"{k}={v}" for k, v in r.items()))
        return rows
    except Exception as e:
        print(f"  ERR: {e}")
        return []

# A. FK de market_signals
q("A. market_signals FK targets", """
SELECT
    kcu.column_name,
    ccu.table_name  AS ref_table,
    ccu.column_name AS ref_column,
    cols.data_type
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON kcu.constraint_name = tc.constraint_name
  AND kcu.table_name = tc.table_name
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.columns cols
  ON cols.table_name  = tc.table_name
 AND cols.column_name = kcu.column_name
WHERE tc.table_name       = 'market_signals'
  AND tc.constraint_type  = 'FOREIGN KEY'
""")

# B. mercurials colonnes completes (deja connu mais confirmer)
q("B. mercurials colonnes", """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'mercurials'
ORDER BY ordinal_position
""")

# C. Tables items / procurement_items
q("C. Tables items candidates", """
SELECT table_name, table_schema
FROM information_schema.tables
WHERE table_name IN (
  'items', 'procurement_items',
  'dict_items', 'item_registry',
  'procurement_dict_items'
)
ORDER BY table_name
""")

# D. Colonnes communes mercurials <-> market_signals
q("D. Colonnes communes mercurials x market_signals", """
SELECT m.column_name AS merc_col,
       m.data_type   AS merc_type,
       ms.column_name AS sig_col,
       ms.data_type  AS sig_type
FROM information_schema.columns m
JOIN information_schema.columns ms
  ON m.data_type = ms.data_type
WHERE m.table_name  = 'mercurials'
  AND ms.table_name = 'market_signals'
  AND m.column_name NOT IN ('id','created_at','updated_at')
  AND ms.column_name NOT IN ('id','created_at','updated_at')
ORDER BY m.column_name, ms.column_name
""")

# E. imc_entries sample
q("E. imc_entries sample (3 lignes)", """
SELECT * FROM public.imc_entries LIMIT 3
""")

# F. market_surveys colonnes cles
q("F. market_surveys colonnes cles", """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'market_surveys'
  AND column_name IN (
    'item_id','item_uid','zone_id',
    'price_per_unit','date_surveyed','validation_status'
  )
ORDER BY column_name
""")

# Bonus G. procurement_dict_items colonnes cles
q("G. procurement_dict_items colonnes cles", """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'procurement_dict_items'
  AND table_schema = 'couche_b'
  AND column_name IN ('id','item_id','item_uid','item_code')
ORDER BY column_name
""")

# Bonus H. market_signals.item_id FK reference exacte via pg_constraint
q("H. market_signals FK via pg_constraint", """
SELECT
    c.conname AS constraint_name,
    a.attname AS column_name,
    af.attname AS ref_column,
    cl2.relname AS ref_table,
    n2.nspname AS ref_schema
FROM pg_constraint c
JOIN pg_class cl ON cl.oid = c.conrelid
JOIN pg_class cl2 ON cl2.oid = c.confrelid
JOIN pg_namespace n2 ON n2.oid = cl2.relnamespace
JOIN pg_attribute a ON a.attrelid = c.conrelid
  AND a.attnum = ANY(c.conkey)
JOIN pg_attribute af ON af.attrelid = c.confrelid
  AND af.attnum = ANY(c.confkey)
WHERE cl.relname = 'market_signals'
  AND c.contype = 'f'
ORDER BY c.conname
""")

conn.close()
print("\n=== PROBE COMPLEMENTAIRE COMPLETE ===")
