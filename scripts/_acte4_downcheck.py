"""ACTE 4 — Vérification post-downgrade 039."""
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'created_at'
        """)
        print("Post-downgrade created_at type:", dict(cur.fetchone()))

        cur.execute("SELECT id, created_at FROM users ORDER BY id LIMIT 5")
        print("Sample values (TEXT restored):")
        for r in cur.fetchall():
            print(" ", dict(r))
