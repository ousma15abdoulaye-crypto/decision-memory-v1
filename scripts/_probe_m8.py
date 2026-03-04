# scripts/_probe_m8.py  ← NE PAS COMMITTER
import os
import psycopg
from psycopg.rows import dict_row

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:

        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='score_runs'
            ) AS ok
        """)
        print("score_runs:", cur.fetchone()["ok"])

        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.views
                WHERE table_schema='public' AND table_name='current_supplier_scores'
            ) AS ok
        """)
        print("current_supplier_scores view:", cur.fetchone()["ok"])

        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='cases'
                  AND column_name='currency'
            ) AS ok
        """)
        print("cases.currency:", cur.fetchone()["ok"])

        # Triggers UPDATE/DELETE + action_statement (preuve opposable)
        cur.execute("""
            SELECT trigger_name, event_manipulation, action_timing, action_statement
            FROM information_schema.triggers
            WHERE trigger_schema='public'
              AND event_object_table='score_runs'
              AND event_manipulation IN ('UPDATE','DELETE')
            ORDER BY trigger_name
        """)
        triggers = cur.fetchall()
        print("Triggers score_runs UPDATE/DELETE:", triggers)

        if not triggers:
            raise SystemExit(
                "\n\U0001f6d1 STOP — aucun trigger UPDATE/DELETE sur score_runs\n"
                "Append-only non garanti DB-level.\n"
                "Remontée CTO obligatoire avant écriture L1."
            )

        print("\n\u2705 Probe OK — artefacts + triggers présents")
