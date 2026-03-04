"""Probe état actuel DB après séquence downgrade."""
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg, psycopg.rows

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row)
conn.autocommit = True

with conn.cursor() as cur:
    # Tables présentes
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('vendors','vendor_identities','market_signals') ORDER BY table_name")
    print("=== TABLES ===")
    for r in cur.fetchall(): print(" ", r["table_name"])

    # Type vendor_id dans market_signals
    cur.execute("SELECT column_name, data_type, udt_name FROM information_schema.columns WHERE table_name='market_signals' AND column_name='vendor_id'")
    r = cur.fetchone()
    print("=== market_signals.vendor_id ===")
    if r: print(f"  data_type={r['data_type']} udt_name={r['udt_name']}")
    else: print("  vendor_id absent")

    # FK sur market_signals
    cur.execute("SELECT constraint_name FROM information_schema.table_constraints WHERE table_name='market_signals' AND constraint_type='FOREIGN KEY'")
    print("=== FKs market_signals ===")
    for r in cur.fetchall(): print(" ", r["constraint_name"])

    # Index sur market_signals
    cur.execute("SELECT indexname FROM pg_indexes WHERE tablename='market_signals'")
    print("=== INDEX market_signals ===")
    for r in cur.fetchall(): print(" ", r["indexname"])

    # Alembic version
    cur.execute("SELECT version_num FROM alembic_version")
    print("=== ALEMBIC VERSION ===")
    for r in cur.fetchall(): print(" ", r["version_num"])

    # Columns count vendors
    cur.execute("SELECT COUNT(*) AS c FROM information_schema.columns WHERE table_name='vendors' AND table_schema='public'")
    r = cur.fetchone()
    print(f"=== vendors colonnes: {r['c'] if r else 'N/A'} ===")

conn.close()
