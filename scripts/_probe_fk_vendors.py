"""Probe FK entrantes vers vendors (post-consolidation) et vendor_identities."""
import os
import psycopg
from psycopg.rows import dict_row

url = os.environ.get("DATABASE_URL", "postgresql+psycopg://dms:dms123@localhost:5432/dms")
url = url.replace("postgresql+psycopg://", "postgresql://")

SQL = """
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name  AS referenced_table,
    ccu.column_name AS referenced_column
FROM information_schema.table_constraints       AS tc
JOIN information_schema.key_column_usage        AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema   = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema   = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name IN ('vendors', 'vendor_identities')
ORDER BY tc.table_name, tc.constraint_name;
"""

with psycopg.connect(url, autocommit=True) as conn:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(SQL)
        rows = cur.fetchall()

print("=== PROBE FK vers vendors / vendor_identities ===")
if rows:
    for r in rows:
        print(dict(r))
else:
    print("AUCUNE FK trouvee")
