"""ACTE 3 — ÉTAPE 2 : schéma pipeline_runs + inspect orphelins."""
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row, autocommit=True) as conn:
    with conn.cursor() as cur:
        # Schéma réel
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'pipeline_runs'
            ORDER BY ordinal_position
        """)
        print("pipeline_runs columns:")
        for r in cur.fetchall():
            print(" ", dict(r))

        # Inspect orphelins avec les vraies colonnes
        cur.execute("""
            SELECT *
            FROM pipeline_runs
            WHERE case_id NOT IN (SELECT id FROM cases)
            ORDER BY case_id
            LIMIT 5
        """)
        print("\nSample orphan rows (5 first, all columns):")
        for r in cur.fetchall():
            print(" ", dict(r))
