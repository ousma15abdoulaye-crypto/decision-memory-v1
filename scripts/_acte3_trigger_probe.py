"""ACTE 3 — Probe trigger append-only pipeline_runs."""
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row, autocommit=True) as conn:
    with conn.cursor() as cur:
        # Triggers sur pipeline_runs
        cur.execute("""
            SELECT tgname, tgenabled, tgtype,
                   pg_get_triggerdef(oid) AS definition
            FROM pg_trigger
            WHERE tgrelid = 'pipeline_runs'::regclass
              AND NOT tgisinternal
        """)
        print("Triggers on pipeline_runs:")
        for r in cur.fetchall():
            print(" ", dict(r))

        # Fonction fn_pipeline_runs_append_only
        cur.execute("""
            SELECT proname, prosrc
            FROM pg_proc
            WHERE proname = 'fn_pipeline_runs_append_only'
        """)
        rows = cur.fetchall()
        print("\nfn_pipeline_runs_append_only:")
        for r in rows:
            print(" ", dict(r))

        # Constraint state
        cur.execute("""
            SELECT conname, convalidated, contype
            FROM pg_constraint
            WHERE conrelid = 'pipeline_runs'::regclass
        """)
        print("\nConstraints on pipeline_runs:")
        for r in cur.fetchall():
            print(" ", dict(r))

        # Orphan count confirmation
        cur.execute("""
            SELECT COUNT(*) AS orphan_count
            FROM pipeline_runs
            WHERE case_id NOT IN (SELECT id FROM cases)
        """)
        print("\nOrphan count (still):", dict(cur.fetchone()))
