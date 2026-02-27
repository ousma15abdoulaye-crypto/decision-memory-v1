"""Vérifie role NOT NULL + CHECK + DEFAULT après migration 037 corrigée."""
import os, psycopg, psycopg.rows
from dotenv import load_dotenv
load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row, autocommit=True)
cur = conn.cursor()

print("=== users.role ===")
cur.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name='users' AND column_name IN ('role','organization')
    ORDER BY column_name
""")
for r in cur.fetchall():
    print(f"  {r['column_name']:<15} | nullable={r['is_nullable']} | default={r['column_default']}")

print()
print("=== CHECK constraint chk_users_role ===")
cur.execute("""
    SELECT constraint_name FROM information_schema.table_constraints
    WHERE table_name='users' AND constraint_name='chk_users_role'
""")
row = cur.fetchone()
print(f"  chk_users_role : {'PRESENTE' if row else 'ABSENTE'}")

print()
print("=== token_blacklist ===")
cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_name='token_blacklist'
""")
row = cur.fetchone()
print(f"  token_blacklist : {'PRESENTE' if row else 'ABSENTE'}")

conn.close()
