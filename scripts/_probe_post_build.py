"""Probe post-build M6."""
from dotenv import load_dotenv
load_dotenv()
load_dotenv(".env.local")
import psycopg
import os
from psycopg.rows import dict_row

url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(url, row_factory=dict_row) as conn:
    for q, lbl in [
        ("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items", "items"),
        ("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_aliases", "aliases"),
        ("SELECT COUNT(*) AS n FROM couche_b.dict_proposals WHERE status='pending'", "proposals pending"),
        ("SELECT COUNT(*) AS n FROM dict_collision_log WHERE collision_type IS NOT NULL", "collision_log M6"),
    ]:
        r = conn.execute(q).fetchone()
        print(f"{lbl}: {r['n']}")
