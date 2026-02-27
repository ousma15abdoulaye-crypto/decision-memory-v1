"""PROBE M1B post-migration 038."""
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=dict_row)
cur = conn.cursor()

print("=== head alembic ===")
cur.execute("SELECT version_num FROM alembic_version")
print(cur.fetchall())

print("\n=== colonnes audit_log ===")
cur.execute(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_name = 'audit_log' ORDER BY ordinal_position"
)
for r in cur.fetchall():
    print(r)

print("\n=== triggers (pg_trigger) ===")
cur.execute(
    "SELECT tgname, tgenabled FROM pg_trigger t "
    "JOIN pg_class c ON t.tgrelid = c.oid "
    "WHERE c.relname = 'audit_log' ORDER BY tgname"
)
for r in cur.fetchall():
    print(r)

print("\n=== fonctions audit ===")
cur.execute(
    "SELECT routine_name FROM information_schema.routines "
    "WHERE routine_schema = 'public' "
    "AND routine_name IN ('fn_verify_audit_chain', 'fn_reject_audit_mutation')"
)
print(cur.fetchall())

print("\n=== sequence chain_seq ===")
cur.execute(
    "SELECT sequence_name FROM information_schema.sequences "
    "WHERE sequence_name = 'audit_log_chain_seq_seq'"
)
print(cur.fetchall())

conn.close()
print("\nPROBE post-migration termine.")
