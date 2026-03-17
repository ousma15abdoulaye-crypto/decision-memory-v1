#!/usr/bin/env python3
"""Check dict_items Railway."""
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

cur.execute("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items")
print(f"procurement_dict_items total : {cur.fetchone()['n']}")

cur.execute("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items WHERE active=TRUE")
print(f"procurement_dict_items active : {cur.fetchone()['n']}")

cur.execute("SELECT item_id, label_fr, taxo_l1, taxo_l3 FROM couche_b.procurement_dict_items LIMIT 3")
for r in cur.fetchall():
    print(f"  {r['item_id'][:30]} | {r['label_fr'][:40]} | {r['taxo_l1']} | {r['taxo_l3']}")

conn.close()
