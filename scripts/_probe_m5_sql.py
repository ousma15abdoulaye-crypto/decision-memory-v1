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

# P1
q1 = "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('mercuriale_sources','mercurials') ORDER BY table_name"
cur.execute(q1)
r1 = cur.fetchall()
print("=== P1 · tables cibles ===")
print(f"Lignes retournees : {len(r1)}")
for r in r1:
    print(r)
if len(r1) == 0:
    print("OK - 0 ligne : tables absentes comme attendu")

# P2 — schema geo_master d'abord
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='geo_master' ORDER BY ordinal_position")
cols = cur.fetchall()
print("\n=== P2 · geo_master schema ===")
for c in cols:
    print(c)

# P2 — sample 10 lignes
cur.execute("SELECT * FROM geo_master LIMIT 10")
r2s = cur.fetchall()
print("\n=== P2 · geo_master sample (10 lignes) ===")
for r in r2s:
    print(r)

# P2 — count
cur.execute("SELECT COUNT(*) AS total FROM geo_master")
r2c = cur.fetchone()
print(f"\n=== P2 · geo_master total ===")
print(r2c)

# P3
cur.execute("SELECT COUNT(*) AS vendors_count FROM vendors")
print("\n=== P3 · vendors count ===")
print(cur.fetchone())

# P4
cur.execute("SELECT version_num FROM alembic_version")
print("\n=== P4 · alembic_version ===")
print(cur.fetchone())

# P5
q5 = "SELECT column_name, udt_name FROM information_schema.columns WHERE table_name='market_signals' AND column_name='vendor_id'"
cur.execute(q5)
print("\n=== P5 · market_signals.vendor_id ===")
print(cur.fetchone())

conn.close()
