"""Probe état réel DB après migration 036."""
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='documents' ORDER BY ordinal_position")
        print("documents columns:", [r["column_name"] for r in cur.fetchall()])

        cur.execute("SELECT indexname FROM pg_indexes WHERE tablename='documents' AND schemaname='public'")
        print("documents indexes:", [r["indexname"] for r in cur.fetchall()])

        cur.execute("SELECT version_num FROM alembic_version")
        print("alembic head:", cur.fetchone()["version_num"])

        for t in ["committee_delegations", "dict_collision_log", "annotation_registry"]:
            cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=%s AND table_schema='public') AS exists", (t,))
            print(f"{t} exists:", cur.fetchone()["exists"])

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name='fk_pipeline_runs_case_id' AND table_name='pipeline_runs') AS exists")
        print("fk_pipeline_runs_case_id:", cur.fetchone()["exists"])
