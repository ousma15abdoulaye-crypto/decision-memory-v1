"""Probe flash M5-PRE-HARDENING — probes SQL A à E."""
import os

import psycopg
from psycopg.rows import dict_row

url = os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url = "postgresql://" + url[len("postgres://"):]

conn = psycopg.connect(url, row_factory=dict_row)

print("=== PROBE A : colonnes market_signals ===")
cur = conn.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name = 'market_signals' ORDER BY ordinal_position"
)
cols = [r["column_name"] for r in cur.fetchall()]
print(cols if cols else "  TABLE ABSENTE ou SANS COLONNES")

print("\n=== PROBE B : existence tables vendor ===")
for tname in ("vendors", "vendor_identities"):
    cur = conn.execute(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables WHERE table_name = %(t)s"
        ") AS exists",
        {"t": tname},
    )
    print(f"  {tname} : {cur.fetchone()['exists']}")

for tname in ("vendors", "vendor_identities"):
    try:
        cur = conn.execute(f"SELECT COUNT(*) AS n FROM {tname}")
        print(f"  COUNT {tname} : {cur.fetchone()['n']}")
    except Exception as e:
        print(f"  COUNT {tname} : ERREUR {e}")

print("\n=== PROBE B2 : SELECT * FROM vendors LIMIT 5 ===")
try:
    cur = conn.execute("SELECT * FROM vendors LIMIT 5")
    rows = cur.fetchall()
    if rows:
        print(f"  colonnes : {list(rows[0].keys())}")
        for r in rows:
            print(f"  {dict(r)}")
    else:
        print("  (vide)")
except Exception as e:
    print(f"  ERREUR : {e}")

print("\n=== PROBE C : FK vers vendors / vendor_identities ===")
cur = conn.execute(
    "SELECT tc.constraint_name, tc.table_name, kcu.column_name, "
    "       ccu.table_name AS foreign_table, ccu.column_name AS foreign_column "
    "FROM information_schema.table_constraints AS tc "
    "JOIN information_schema.key_column_usage AS kcu "
    "    ON tc.constraint_name = kcu.constraint_name "
    "JOIN information_schema.constraint_column_usage AS ccu "
    "    ON ccu.constraint_name = tc.constraint_name "
    "WHERE tc.constraint_type = 'FOREIGN KEY' "
    "  AND ccu.table_name IN ('vendors', 'vendor_identities') "
    "ORDER BY tc.table_name, tc.constraint_name"
)
fks = cur.fetchall()
if fks:
    for r in fks:
        print(f"  {r['table_name']}.{r['column_name']} -> "
              f"{r['foreign_table']}.{r['foreign_column']}  "
              f"[{r['constraint_name']}]")
else:
    print("  AUCUNE FK")

print("\n=== PROBE D : contraintes vendor_identities ===")
try:
    cur = conn.execute(
        "SELECT conname, contype FROM pg_constraint "
        "WHERE conrelid = 'vendor_identities'::regclass ORDER BY conname"
    )
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  {r['conname']}  type={r['contype']}")
    else:
        print("  AUCUNE contrainte")
except Exception as e:
    print(f"  ERREUR : {e}")

print("\n=== PROBE E : index vendors + vendor_identities ===")
cur = conn.execute(
    "SELECT indexname, tablename FROM pg_indexes "
    "WHERE tablename IN ('vendors', 'vendor_identities') "
    "ORDER BY tablename, indexname"
)
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  {r['tablename']} · {r['indexname']}")
else:
    print("  AUCUN index")

conn.close()
print("\n=== FIN PROBES ===")
