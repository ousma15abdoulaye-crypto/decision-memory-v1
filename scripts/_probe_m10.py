import os
import psycopg
from psycopg.rows import dict_row

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='cases'
            ORDER BY ordinal_position
        """)
        print("=== cases colonnes ===")
        for r in cur.fetchall():
            print(r)

        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            ORDER BY table_name
        """)
        print("\n=== tables public ===")
        for r in cur.fetchall():
            print(r["table_name"])

        cur.execute("""
            SELECT trigger_name, event_object_table, event_manipulation
            FROM information_schema.triggers
            WHERE trigger_schema='public'
            ORDER BY event_object_table, event_manipulation
        """)
        print("\n=== triggers existants ===")
        for r in cur.fetchall():
            print(r)

        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name IN ('pipeline_runs', 'pipeline_step_runs')
        """)
        print("\n=== tables pipeline existantes ===")
        rows = cur.fetchall()
        for r in rows:
            print(r["table_name"])
        if rows:
            print("STOP — migration fantome detectee")
        else:
            print("PASS — pipeline_runs absente — migration saine")
