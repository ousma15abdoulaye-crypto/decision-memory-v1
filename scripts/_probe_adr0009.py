import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv(Path(__file__).parent.parent / ".env")


def q(cur, sql, params=None):
    cur.execute(sql, params or ())
    return cur.fetchall()


url = os.environ.get("DATABASE_URL", os.environ.get("DM_DATABASE_URL", ""))
if not url:
    raise SystemExit("DATABASE_URL missing")
url = url.replace("postgresql+psycopg://", "postgresql://")

conn = psycopg.connect(url, row_factory=dict_row)
conn.autocommit = True
cur = conn.cursor()

print("=== scoring_configs columns ===")
rows = q(cur, """
select column_name, data_type, column_default, is_nullable
from information_schema.columns
where table_schema='public' and table_name='scoring_configs'
order by ordinal_position
""")
for r in rows:
    print(r)

print("\n=== scoring_configs count + sample ===")
print(q(cur, "select count(*) as n from public.scoring_configs")[0])
for r in q(cur, "select * from public.scoring_configs limit 10"):
    print(r)

print("\n=== mercuriale_raw_queue columns ===")
rows = q(cur, """
select column_name, data_type
from information_schema.columns
where table_schema='couche_b' and table_name='mercuriale_raw_queue'
order by ordinal_position
""")
for r in rows:
    print(r)

print("\n=== mercuriale_raw_queue count ===")
print(q(cur, "select count(*) as n from couche_b.mercuriale_raw_queue")[0])

print("\n=== submission_scores columns ===")
rows = q(cur, """
select column_name, data_type
from information_schema.columns
where table_schema='public' and table_name='submission_scores'
order by ordinal_position
""")
for r in rows:
    print(r)

print("\n=== supplier_scores columns ===")
rows = q(cur, """
select column_name, data_type
from information_schema.columns
where table_schema='public' and table_name='supplier_scores'
order by ordinal_position
""")
for r in rows:
    print(r)

cur.close()
conn.close()
print("\nOK: probe done")
