"""PROBE post-migration 037."""
import os
import psycopg
import psycopg.rows
from dotenv import load_dotenv

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row, autocommit=True)
cur = conn.cursor()

print("=== alembic_version ===")
cur.execute("SELECT version_num FROM alembic_version")
for r in cur.fetchall():
    print(f"  {r['version_num']}")

print()
print("=== COLONNES users (nouvelles) ===")
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'users'
      AND column_name IN ('role', 'organization')
    ORDER BY column_name
""")
rows = cur.fetchall()
for r in rows:
    print(f"  {r['column_name']:<20} | {r['data_type']:<15} | nullable={r['is_nullable']}")
if not rows:
    print("  ABSENT — probleme migration")

print()
print("=== token_blacklist — colonnes ===")
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'token_blacklist'
    ORDER BY ordinal_position
""")
rows = cur.fetchall()
for r in rows:
    print(f"  {r['column_name']:<20} | {r['data_type']:<25} | nullable={r['is_nullable']}")
if not rows:
    print("  ABSENTE — probleme migration")

print()
print("=== INDEX token_blacklist ===")
cur.execute("""
    SELECT indexname FROM pg_indexes
    WHERE tablename = 'token_blacklist'
    ORDER BY indexname
""")
for r in cur.fetchall():
    print(f"  {r['indexname']}")

print()
print("=== fn_cleanup_expired_tokens ===")
cur.execute("""
    SELECT proname FROM pg_proc
    WHERE proname = 'fn_cleanup_expired_tokens'
""")
row = cur.fetchone()
print(f"  {'PRESENTE' if row else 'ABSENTE'}")

print()
print("=== ZERO touche audit_log ===")
cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_name = 'audit_log' AND table_schema = 'public'
""")
row = cur.fetchone()
print(f"  audit_log : {'PRESENTE (attention!)' if row else 'ABSENTE (correct)'}")

conn.close()
