"""Probe post-downgrade · tables M6 supprimées + couche_b intacte."""
from dotenv import load_dotenv
load_dotenv()
load_dotenv(".env.local")
import psycopg
import os
from psycopg.rows import dict_row

url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not url:
    print("DATABASE_URL non definie")
    exit(1)

with psycopg.connect(url, row_factory=dict_row) as conn:
    rows = conn.execute(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_name IN (
            'dict_items','dict_aliases',
            'dict_proposals','dict_item_families',
            'dict_item_categories'
        )
        AND table_schema = 'public'
        """
    ).fetchall()
    print("Tables M6 publiques restantes :", rows)

    rows = conn.execute(
        "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items"
    ).fetchone()
    print("couche_b.procurement_dict_items :", rows["n"], "lignes")

    rows = conn.execute(
        "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_aliases"
    ).fetchone()
    print("couche_b.procurement_dict_aliases :", rows["n"], "lignes")
