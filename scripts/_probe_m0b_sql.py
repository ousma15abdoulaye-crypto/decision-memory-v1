"""PROBE-SQL-01 — M0B DB Hardening"""
import os, sys
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

queries = {
    "1. Tables publiques": """
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' ORDER BY tablename;
    """,
    "2. pipeline_runs existe": """
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_name = 'pipeline_runs'
        ) AS pipeline_runs_exists;
    """,
    "3. FK pipeline_runs": """
        SELECT tc.constraint_name, kcu.column_name,
               ccu.table_name AS foreign_table
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_name = 'pipeline_runs';
    """,
    "4. committee_delegations existe": """
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_name = 'committee_delegations'
        ) AS delegations_exists;
    """,
    "5. dict_collision_log existe": """
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_name = 'dict_collision_log'
        ) AS collision_log_exists;
    """,
    "6. extraction_jobs colonnes": """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'extraction_jobs'
        ORDER BY ordinal_position;
    """,
    "7. annotation_registry existe": """
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_name = 'annotation_registry'
        ) AS annotation_registry_exists;
    """,
    "8. role app_user existe": """
        SELECT EXISTS (
          SELECT 1 FROM pg_roles WHERE rolname = 'app_user'
        ) AS app_user_exists;
    """,
    "9. Triggers existants": """
        SELECT trigger_name, event_object_table, event_manipulation
        FROM information_schema.triggers
        WHERE trigger_schema = 'public'
        ORDER BY event_object_table;
    """,
    "10. Index existants": """
        SELECT indexname, tablename FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """,
}

with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        for label, sql in queries.items():
            print(f"\n{'='*60}")
            print(f"=== {label}")
            print('='*60)
            try:
                cur.execute(sql)
                rows = cur.fetchall()
                if not rows:
                    print("  (aucun résultat)")
                for row in rows:
                    print(" ", dict(row))
            except Exception as e:
                print(f"  ERREUR: {e}")
