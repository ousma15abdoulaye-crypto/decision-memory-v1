import os, psycopg, psycopg.rows
from dotenv import load_dotenv
load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row, autocommit=True)
cur = conn.cursor()

print("=== COMMANDE 2 — colonnes documents ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'documents'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r['column_name']:<30} | {r['data_type']}")

print()
print("=== COMMANDE 3 — FK NOT VALID ===")
cur.execute("""
    SELECT conname, convalidated
    FROM pg_constraint
    WHERE conname = 'fk_pipeline_runs_case_id'
""")
row = cur.fetchone()
if row:
    print(f"  conname      = {row['conname']}")
    print(f"  convalidated = {row['convalidated']}")
else:
    print("  ABSENT")

print()
print("=== COMMANDE 4 — tables 036 ===")
cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_name IN (
        'committee_delegations', 'dict_collision_log', 'annotation_registry'
    )
    ORDER BY table_name
""")
for r in cur.fetchall():
    print(f"  {r['table_name']}")

conn.close()
