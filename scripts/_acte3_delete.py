"""ACTE 3 — ÉTAPES 3→6 : DELETE orphelins + VALIDATE CONSTRAINT."""
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row, autocommit=False) as conn:
    with conn.cursor() as cur:

        # ÉTAPE 3 — DELETE orphelins
        cur.execute("""
            DELETE FROM pipeline_runs
            WHERE case_id NOT IN (SELECT id FROM cases)
        """)
        deleted = cur.rowcount
        print(f"ETAPE 3 - DELETE: {deleted} lignes supprimees")

        conn.commit()

        # ÉTAPE 4 — confirmer orphan_count_after = 0
        cur.execute("""
            SELECT COUNT(*) AS orphan_count_after
            FROM pipeline_runs
            WHERE case_id NOT IN (SELECT id FROM cases)
        """)
        after = dict(cur.fetchone())
        print(f"ETAPE 4 - orphan_count_after: {after}")

        if after["orphan_count_after"] != 0:
            print("STOP-M2B-3 — orphan_count_after > 0 — VALIDATE CONSTRAINT annule")
        else:
            # ÉTAPE 5 — VALIDATE CONSTRAINT
            print("ETAPE 5 - VALIDATE CONSTRAINT fk_pipeline_runs_case_id...")
            cur.execute("""
                ALTER TABLE pipeline_runs
                  VALIDATE CONSTRAINT fk_pipeline_runs_case_id
            """)
            conn.commit()
            print("ETAPE 5 - VALIDATE CONSTRAINT OK")

            # ÉTAPE 6 — confirmer convalidated = true
            cur.execute("""
                SELECT conname, convalidated, conrelid::regclass AS table_name
                FROM pg_constraint
                WHERE conrelid = 'pipeline_runs'::regclass
                  AND conname = 'fk_pipeline_runs_case_id'
            """)
            result = dict(cur.fetchone())
            print(f"ETAPE 6 - constraint state: {result}")
