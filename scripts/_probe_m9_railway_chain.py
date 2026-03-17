#!/usr/bin/env python3
"""Probe Railway migration chain et dict state."""
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

db = os.environ.get("RAILWAY_DATABASE_URL","").replace("postgresql+psycopg://","postgresql://")
conn = psycopg.connect(db, row_factory=dict_row, autocommit=True)
cur = conn.cursor()

print("=== alembic_version Railway ===")
cur.execute("SELECT version_num FROM alembic_version")
for r in cur.fetchall(): print(f"  {r['version_num']}")

print("\n=== procurement_dict_items counts ===")
cur.execute("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items")
print(f"  total: {cur.fetchone()['n']}")
cur.execute("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items WHERE active=TRUE")
print(f"  active: {cur.fetchone()['n']}")

print("\n=== couche_b tables Railway ===")
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='couche_b' ORDER BY table_name")
for r in cur.fetchall(): print(f"  {r['table_name']}")

print("\n=== m6_dictionary_build migration existe? ===")
# Check if m6 migration was applied (it might be tracked differently)
try:
    cur.execute("SELECT 1 FROM information_schema.columns WHERE table_schema='couche_b' AND table_name='procurement_dict_items' AND column_name='canonical_slug'")
    r = cur.fetchone()
    print(f"  canonical_slug colonne: {'OUI' if r else 'NON'}")
except Exception as e:
    print(f"  ERR: {e}")

conn.close()
