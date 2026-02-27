"""PROBE M1 — étapes 0.3 à 0.6"""
import os
import psycopg
import psycopg.rows
from dotenv import load_dotenv

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row, autocommit=True)
cur = conn.cursor()

print("=== 0.3 TABLES AUTH PRESENTES ===")
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN ('users', 'token_blacklist', 'audit_log')
    ORDER BY table_name
""")
rows = cur.fetchall()
for r in rows:
    print(f"  {r['table_name']}")
if not rows:
    print("  (aucune)")

print()
print("=== 0.4 COLONNES users ===")
cur.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'users'
    ORDER BY ordinal_position
""")
rows = cur.fetchall()
for r in rows:
    print(f"  {r['column_name']:<20} | {r['data_type']:<20} | nullable={r['is_nullable']} | default={r['column_default']}")
if not rows:
    print("  (table absente ou vide)")

print()
print("=== 0.5 COLONNES token_blacklist ===")
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'token_blacklist'
    ORDER BY ordinal_position
""")
rows = cur.fetchall()
for r in rows:
    print(f"  {r['column_name']:<20} | {r['data_type']:<20} | nullable={r['is_nullable']}")
if not rows:
    print("  (table absente ou vide)")

print()
print("=== 0.6 INDEX sur tables auth ===")
cur.execute("""
    SELECT indexname, tablename
    FROM pg_indexes
    WHERE tablename IN ('users', 'token_blacklist')
    ORDER BY tablename, indexname
""")
rows = cur.fetchall()
for r in rows:
    print(f"  {r['tablename']:<20} | {r['indexname']}")
if not rows:
    print("  (aucun index)")

conn.close()
