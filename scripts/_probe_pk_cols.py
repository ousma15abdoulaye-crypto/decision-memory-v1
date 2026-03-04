"""Probe PK columns for tables used in 036 migration."""
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

tables = ["committees", "committee_members", "cases", "documents", "procurement_references"]

with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        for t in tables:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (t,))
            rows = cur.fetchall()
            print(f"\n=== {t} ===")
            for r in rows:
                print(f"  {r['column_name']} : {r['data_type']}")
