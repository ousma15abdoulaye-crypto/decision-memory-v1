"""PROBE M1B — état DB avant migration 038."""
import os

from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=dict_row)
cur = conn.cursor()

print("=== 0.3 audit_log presente ===")
cur.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema = 'public' AND table_name = 'audit_log'"
)
print(cur.fetchall())

print("\n=== 0.4 colonnes audit_log ===")
cur.execute(
    "SELECT column_name, data_type, is_nullable, column_default "
    "FROM information_schema.columns "
    "WHERE table_name = 'audit_log' "
    "ORDER BY ordinal_position"
)
rows = cur.fetchall()
if rows:
    for r in rows:
        print(r)
else:
    print("(aucune colonne — table absente)")

print("\n=== 0.5 triggers sur audit_log ===")
cur.execute(
    "SELECT trigger_name, event_manipulation, action_timing "
    "FROM information_schema.triggers "
    "WHERE event_object_table = 'audit_log' "
    "ORDER BY trigger_name"
)
print(cur.fetchall())

print("\n=== 0.6 pgcrypto ===")
cur.execute(
    "SELECT extname, extversion FROM pg_extension WHERE extname = 'pgcrypto'"
)
print(cur.fetchall())

print("\n=== 0.7 fonctions audit ===")
cur.execute(
    "SELECT routine_name FROM information_schema.routines "
    "WHERE routine_schema = 'public' "
    "AND routine_name IN ('fn_verify_audit_chain', 'fn_reject_audit_mutation')"
)
print(cur.fetchall())

conn.close()
print("\nPROBE termine.")
