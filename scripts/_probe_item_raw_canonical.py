"""Probe item_raw vs item_canonical · avant GO import."""
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
    print("=== item_canonical (5 lignes) ===")
    rows = conn.execute(
        """
        SELECT item_canonical
        FROM mercurials
        WHERE item_canonical IS NOT NULL
        LIMIT 5
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== item_canonical NULL count ===")
    r = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            COUNT(item_canonical) AS with_canonical
        FROM mercurials
        """
    ).fetchone()
    print(" ", dict(r))

    print("=== Colonnes mercurials (schema) ===")
    rows = conn.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'mercurials'
        ORDER BY ordinal_position
        """
    ).fetchall()
    print(" ", [x["column_name"] for x in rows])
