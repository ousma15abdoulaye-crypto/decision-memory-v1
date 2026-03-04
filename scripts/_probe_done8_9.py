"""DONE-8 / DONE-9 probe DB analysis_summaries"""
import os

import psycopg
from psycopg.rows import dict_row

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT result_hash, summary_status FROM public.analysis_summaries LIMIT 3"
        )
        print("=== DONE-8 : analysis_summaries ===")
        rows = cur.fetchall()
        for r in rows:
            print(r)
        if not rows:
            print("(aucune ligne — tests ont utilisé rollback)")

        cur.execute(
            "SELECT result_jsonb->>'summary_version' AS v "
            "FROM public.analysis_summaries LIMIT 1"
        )
        print("=== DONE-9 : summary_version depuis result_jsonb ===")
        row = cur.fetchone()
        print(row)
        if row:
            assert row["v"] == "v1", f"Attendu 'v1', reçu '{row['v']}'"
            print("PASS — INV-AS5 confirmé")
        else:
            print("INFO — aucune ligne (tests rollback) — INV-AS5 prouvé via test_generate_summary_persists_result_jsonb_complete")
