"""Probe complet mandat V2 — SQL A B C D E + alembic_version brut."""
import os
import psycopg
from psycopg.rows import dict_row

url = os.environ.get("DATABASE_URL", "postgresql://dms:dms123@localhost:5432/dms")
if url.startswith("postgresql+psycopg://"):
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)
if url.startswith("postgres://"):
    url = "postgresql://" + url[len("postgres://"):]

conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)

print("=== alembic_version brut ===")
cur = conn.execute("SELECT version_num FROM alembic_version")
print(cur.fetchall())

print("\n=== SQL A · colonnes market_signals ===")
cur = conn.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name = 'market_signals' ORDER BY ordinal_position"
)
for r in cur.fetchall(): print(" ", r["column_name"])

print("\n=== SQL B · existence et counts ===")
cur = conn.execute("""
SELECT
  EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='vendors') AS vendors_exists,
  EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='vendor_identities') AS vendor_identities_exists
""")
print(cur.fetchone())

for tname in ("vendors", "vendor_identities"):
    try:
        cur = conn.execute(f"SELECT COUNT(*) AS n FROM {tname}")
        print(f"  COUNT {tname}: {cur.fetchone()['n']}")
    except Exception as e:
        print(f"  COUNT {tname}: ERREUR — {e}")

print("\n  SELECT * FROM vendors LIMIT 5:")
try:
    cur = conn.execute("SELECT * FROM vendors LIMIT 5")
    rows = cur.fetchall()
    if rows:
        print("  colonnes:", list(rows[0].keys()))
        for r in rows: print(" ", dict(r))
    else:
        print("  (vide)")
except Exception as e:
    print(f"  ERREUR — {e}")

print("\n=== SQL C · FK entrantes vers vendors / vendor_identities ===")
cur = conn.execute("""
SELECT
    tc.table_name         AS dependent_table,
    kcu.column_name       AS dependent_column,
    ccu.table_name        AS referenced_table,
    ccu.column_name       AS referenced_column,
    tc.constraint_name
FROM information_schema.table_constraints       AS tc
JOIN information_schema.key_column_usage        AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema   = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema   = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name IN ('vendors', 'vendor_identities')
""")
rows = cur.fetchall()
if rows:
    for r in rows: print(" ", dict(r))
else:
    print("  AUCUNE FK")

print("\n=== SQL D · contraintes vendors (ex vendor_identities) ===")
try:
    cur = conn.execute(
        "SELECT conname, contype FROM pg_constraint "
        "WHERE conrelid = 'vendors'::regclass ORDER BY conname"
    )
    for r in cur.fetchall(): print(f"  {r['conname']}  type={r['contype']}")
except Exception as e:
    print(f"  ERREUR — {e}")

print("\n=== SQL D2 · contraintes vendor_identities (si existe) ===")
try:
    cur = conn.execute(
        "SELECT conname, contype FROM pg_constraint "
        "WHERE conrelid = 'vendor_identities'::regclass ORDER BY conname"
    )
    rows = cur.fetchall()
    if rows:
        for r in rows: print(f"  {r['conname']}  type={r['contype']}")
    else:
        print("  (aucune)")
except Exception as e:
    print(f"  table vendor_identities absente — {e}")

print("\n=== SQL E · index vendors + vendor_identities ===")
cur = conn.execute(
    "SELECT indexname, tablename, indexdef FROM pg_indexes "
    "WHERE tablename IN ('vendors', 'vendor_identities') "
    "ORDER BY tablename, indexname"
)
rows = cur.fetchall()
if rows:
    for r in rows: print(f"  {r['tablename']} · {r['indexname']}")
else:
    print("  AUCUN")

conn.close()
print("\n=== FIN PROBE V2 ===")
