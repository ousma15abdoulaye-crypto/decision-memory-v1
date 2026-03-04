"""ACTE 6 — Probe cases référencant le compte smoke id=10."""
import sys
import psycopg
from psycopg.rows import dict_row

url = sys.argv[1]

with psycopg.connect(url, row_factory=dict_row, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, title, case_type, owner_id, created_at
            FROM cases
            WHERE owner_id = 10
            ORDER BY id
        """)
        rows = cur.fetchall()
        print(f"Cases owned by id=10 : {len(rows)} ligne(s)")
        for r in rows:
            print(" ", dict(r))

        cur.execute("SELECT COUNT(*) AS total_cases FROM cases")
        print("Total cases in DB:", dict(cur.fetchone()))

del url
