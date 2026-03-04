import sys, os
sys.path.insert(0, ".")
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

db_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(db_url, row_factory=dict_row)
conn.autocommit = True
cur = conn.cursor()

cur.execute("SELECT COUNT(*) AS total FROM geo_master")
print(f"geo_master total : {cur.fetchone()['total']} zones")

cur.execute("SELECT name, level, type, parent_id FROM geo_master ORDER BY level, name")
rows = cur.fetchall()
for r in rows:
    print(r)

conn.close()
