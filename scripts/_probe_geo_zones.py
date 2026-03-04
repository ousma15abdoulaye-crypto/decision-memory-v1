"""Probe : liste les zones geo_master actuelles."""
import psycopg

url = "postgresql://dms:dms123@localhost:5432/dms"
with psycopg.connect(url, row_factory=psycopg.rows.dict_row) as conn:
    rows = conn.execute(
        "SELECT id, name, level, type FROM geo_master ORDER BY level, name"
    ).fetchall()
    for r in rows:
        print(r)
    print(f"\nTotal : {len(rows)} zones")
