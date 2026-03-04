"""Probe alembic_version table — multiple heads?"""
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg, psycopg.rows

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row)
conn.autocommit = True

with conn.cursor() as cur:
    cur.execute("SELECT version_num FROM alembic_version ORDER BY version_num")
    rows = cur.fetchall()
    print(f"alembic_version rows ({len(rows)}):")
    for r in rows: print(f"  {r['version_num']}")

    # Also check privilege on market_signals
    print("\n=== FK confdeltype ===")
    cur.execute("""
        SELECT c.conname, c.confdeltype,
               CASE c.confdeltype WHEN 'r' THEN 'RESTRICT' WHEN 'n' THEN 'SET NULL'
               WHEN 'a' THEN 'NO ACTION' ELSE c.confdeltype END AS label
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE c.conname = 'market_signals_vendor_id_fkey'
          AND t.relname = 'market_signals'
    """)
    r = cur.fetchone()
    if r: print(f"  {r['conname']}: confdeltype={r['confdeltype']} ({r['label']})")
    else: print("  FK absente")

conn.close()
