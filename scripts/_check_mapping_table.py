#!/usr/bin/env python3
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass
import psycopg
from psycopg.rows import dict_row

db = os.environ.get("RAILWAY_DATABASE_URL","").replace("postgresql+psycopg://","postgresql://")
conn = psycopg.connect(db, row_factory=dict_row, autocommit=True)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_name='mercurials_item_map'")
exists = cur.fetchone()["n"]
print(f"mercurials_item_map existe: {exists}")

if exists:
    cur.execute("SELECT COUNT(*) AS n FROM public.mercurials_item_map")
    print(f"Lignes: {cur.fetchone()['n']}")

cur.execute("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items WHERE active=TRUE")
print(f"Dict actifs: {cur.fetchone()['n']}")

conn.close()
