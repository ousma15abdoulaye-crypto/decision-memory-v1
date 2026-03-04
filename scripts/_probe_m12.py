"""
scripts/_probe_m12.py — NON COMMITÉ — JAMAIS git add
Probe DB pré-flight M12.
"""
import json
import os

import psycopg
from psycopg.rows import dict_row

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:

        # 1. Colonnes pipeline_runs
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='pipeline_runs'
            ORDER BY ordinal_position
        """)
        print("=== pipeline_runs colonnes ===")
        for r in cur.fetchall():
            print(r)

        # 2. result_jsonb présent ?
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='pipeline_runs'
              AND column_name='result_jsonb'
        """)
        has_jsonb = bool(cur.fetchone())
        print(f"\npipeline_runs.result_jsonb présent : {has_jsonb}")
        if not has_jsonb:
            print("🛑 STOP — result_jsonb absent")

        # 3. CAS v1 réels
        cur.execute("""
            SELECT
                pipeline_run_id::TEXT,
                result_jsonb->>'cas_version'        AS cas_version,
                result_jsonb->>'case_id'            AS case_id,
                result_jsonb->'pipeline'->>'mode'   AS mode,
                result_jsonb->'pipeline'->>'status' AS pipeline_status
            FROM public.pipeline_runs
            WHERE result_jsonb IS NOT NULL
              AND result_jsonb != '{}'::jsonb
            ORDER BY created_at DESC
            LIMIT 3
        """)
        print("\n=== CAS v1 réels dans pipeline_runs ===")
        rows = cur.fetchall()
        for r in rows:
            print(r)
        if not rows:
            print("⚠️  Aucun CAS v1 persisté — tests utiliseront pipeline_run_factory")

        # 4. Anti-fantôme analysis_summaries
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name='analysis_summaries'
        """)
        exists = cur.fetchone()
        if exists:
            print("\n🛑 STOP — analysis_summaries existe déjà (fantôme / divergence)")
        else:
            print("\nPASS — analysis_summaries absente — migration 035 saine")

        # 5. Vérification UUID pipeline_run_id
        cur.execute("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='pipeline_runs'
              AND column_name='pipeline_run_id'
        """)
        pk_type = cur.fetchone()
        print(f"\npipeline_runs.pipeline_run_id type : {pk_type}")
        if pk_type and pk_type.get("data_type") == "uuid":
            print("PASS — UUID confirmé — FK DB réelle possible")
        else:
            print("🛑 STOP — pipeline_run_id type != uuid")
