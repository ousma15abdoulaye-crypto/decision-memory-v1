"""Probe DoD M0B — 6 vérifications."""
import os
import psycopg
import psycopg.rows
from dotenv import load_dotenv

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row, autocommit=True)
cur = conn.cursor()

print("=" * 60)
print("# 2. COLONNES documents")
print("=" * 60)
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'documents'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r['column_name']:30s} | {r['data_type']}")

print()
print("=" * 60)
print("# 3. FK NOT VALID — fk_pipeline_runs_case_id")
print("=" * 60)
cur.execute("""
    SELECT conname, convalidated
    FROM pg_constraint
    WHERE conname = 'fk_pipeline_runs_case_id'
""")
row = cur.fetchone()
if row:
    print(f"  conname      = {row['conname']}")
    print(f"  convalidated = {row['convalidated']}  (False = NOT VALID = attendu)")
else:
    print("  ABSENT — FK non trouvee")

print()
print("=" * 60)
print("# 4. TABLES creees par 036")
print("=" * 60)
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_name IN (
        'committee_delegations',
        'dict_collision_log',
        'annotation_registry'
    )
    ORDER BY table_name
""")
for r in cur.fetchall():
    print(f"  {r['table_name']}")

print()
print("=" * 60)
print("# BONUS — extraction_jobs colonnes async")
print("=" * 60)
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'extraction_jobs'
      AND column_name IN ('next_retry_at', 'fallback_used', 'retry_count', 'max_retries', 'queued_at')
    ORDER BY column_name
""")
for r in cur.fetchall():
    print(f"  {r['column_name']}")

print()
print("=" * 60)
print("# BONUS — UNIQUE uq_documents_case_sha256")
print("=" * 60)
cur.execute("""
    SELECT constraint_name
    FROM information_schema.table_constraints
    WHERE constraint_name = 'uq_documents_case_sha256'
      AND table_name = 'documents'
""")
row = cur.fetchone()
print(f"  uq_documents_case_sha256 : {'PRESENTE' if row else 'ABSENTE'}")

print()
print("=" * 60)
print("# BONUS — Index idx_documents_case_id")
print("=" * 60)
cur.execute("""
    SELECT indexname FROM pg_indexes
    WHERE tablename = 'documents' AND indexname = 'idx_documents_case_id'
""")
row = cur.fetchone()
print(f"  idx_documents_case_id : {'PRESENT' if row else 'ABSENT'}")

conn.close()
