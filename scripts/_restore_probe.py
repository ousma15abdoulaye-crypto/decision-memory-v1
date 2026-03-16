"""Probe schema + restore seeds."""
import os

import psycopg

url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://").replace("postgres://", "postgresql://")
with psycopg.connect(url) as c:
    r = c.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'couche_b' AND table_name = 'procurement_dict_items'
        ORDER BY ordinal_position
    """).fetchall()
    for row in r:
        print(row[0], row[1], row[2])
