"""ACTE 4 — Vérification post-upgrade migration 039."""
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row, autocommit=True) as conn:
    with conn.cursor() as cur:
        # Étape 3 — type colonne
        cur.execute("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'created_at'
        """)
        print("ETAPE 3 - created_at column type:")
        print(" ", dict(cur.fetchone()))

        # Étape 4 — valeurs
        cur.execute("""
            SELECT id, created_at, pg_typeof(created_at) AS pg_type
            FROM users ORDER BY id LIMIT 5
        """)
        print("\nETAPE 4 - sample values:")
        for r in cur.fetchall():
            print(" ", dict(r))
