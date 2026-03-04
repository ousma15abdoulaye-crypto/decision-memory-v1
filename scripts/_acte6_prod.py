"""ACTE 6 — Runbook prod Railway.

Usage : python scripts/_acte6_prod.py <RAILWAY_DB_URL>
Ne pas hardcoder l'URL. URL effacée de mémoire après usage.
"""
import sys
import psycopg
from psycopg.rows import dict_row

if len(sys.argv) < 2:
    print("Usage: python scripts/_acte6_prod.py <DATABASE_URL>")
    sys.exit(1)

url = sys.argv[1]

with psycopg.connect(url, row_factory=dict_row, autocommit=False) as conn:
    with conn.cursor() as cur:

        # Vérifier created_at post-migration 039
        cur.execute("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'created_at'
        """)
        print("created_at post-039:", dict(cur.fetchone()))

        cur.execute("""
            SELECT id, created_at, pg_typeof(created_at) AS pg_type
            FROM users ORDER BY id LIMIT 5
        """)
        print("Sample values:")
        for r in cur.fetchall():
            print(" ", dict(r))

        # PROBE orphelins (re-confirmation)
        cur.execute("""
            SELECT COUNT(*) AS orphan_count
            FROM pipeline_runs
            WHERE case_id NOT IN (SELECT id FROM cases)
        """)
        orphan = dict(cur.fetchone())
        print("\nOrphan count:", orphan)

        if orphan["orphan_count"] == 0:
            # VALIDATE CONSTRAINT
            cur.execute("""
                ALTER TABLE pipeline_runs
                  VALIDATE CONSTRAINT fk_pipeline_runs_case_id
            """)
            conn.commit()
            print("VALIDATE CONSTRAINT: OK")

            # Confirmer convalidated
            cur.execute("""
                SELECT conname, convalidated, conrelid::regclass AS table_name
                FROM pg_constraint
                WHERE conrelid = 'pipeline_runs'::regclass
                  AND conname = 'fk_pipeline_runs_case_id'
            """)
            print("Constraint state:", dict(cur.fetchone()))
        else:
            conn.rollback()
            print("STOP-M2B-3 — orphan_count > 0 — VALIDATE annule")

        # alembic version
        cur.execute("SELECT version_num FROM alembic_version")
        print("\nalembic_version:", dict(cur.fetchone()))

# URL purgée de la variable après usage (hors scope)
del url
