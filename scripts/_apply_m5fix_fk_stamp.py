"""
Correctif état partiel m5_fix local.

Situation :
  - vendor_id déjà UUID (type changé lors d'une run précédente)
  - FK market_signals_vendor_id_fkey absente
  - alembic current = m5_pre_vendors_consolidation
  - idx_signals_vendor existe (recréé automatiquement par PostgreSQL lors du type change)

Action :
  1. Ajouter FK RESTRICT (si absente)
  2. alembic stamp m5_fix_market_signals_vendor_type
"""

import os
import subprocess

from dotenv import load_dotenv

load_dotenv()
import psycopg
import psycopg.rows

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row)
conn.autocommit = True

# Vérifier état
with conn.cursor() as cur:
    cur.execute(
        "SELECT udt_name FROM information_schema.columns "
        "WHERE table_name='market_signals' AND column_name='vendor_id'"
    )
    r = cur.fetchone()
    vendor_id_type = r["udt_name"] if r else None
    print(f"market_signals.vendor_id type : {vendor_id_type}")

    cur.execute(
        "SELECT constraint_name FROM information_schema.table_constraints "
        "WHERE constraint_name='market_signals_vendor_id_fkey' "
        "AND table_name='market_signals' AND constraint_type='FOREIGN KEY'"
    )
    fk_exists = cur.fetchone() is not None
    print(f"FK market_signals_vendor_id_fkey existe : {fk_exists}")

assert vendor_id_type == "uuid", f"STOP : vendor_id type inattendu : {vendor_id_type}"

if not fk_exists:
    print("\n=== AJOUT FK ON DELETE RESTRICT ===")
    with conn.cursor() as cur:
        cur.execute("""
            ALTER TABLE market_signals
                ADD CONSTRAINT market_signals_vendor_id_fkey
                FOREIGN KEY (vendor_id)
                REFERENCES vendors(id)
                ON DELETE RESTRICT
        """)
    print("  FK ajoutée")
else:
    print("FK déjà présente — vérifier confdeltype")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.confdeltype,
                   CASE c.confdeltype
                       WHEN 'r' THEN 'RESTRICT'
                       WHEN 'n' THEN 'SET NULL'
                       WHEN 'a' THEN 'NO ACTION'
                       WHEN 'c' THEN 'CASCADE'
                       ELSE 'UNKNOWN'
                   END AS label
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE c.conname = 'market_signals_vendor_id_fkey'
              AND t.relname = 'market_signals'
              AND c.contype = 'f'
        """)
        r = cur.fetchone()
        if r:
            print(f"  confdeltype={r['confdeltype']} ({r['label']})")
            if r["confdeltype"] != "r":
                print("  CORRECTION : drop + recréation RESTRICT")
                cur.execute(
                    "ALTER TABLE market_signals DROP CONSTRAINT market_signals_vendor_id_fkey"
                )
                cur.execute("""
                    ALTER TABLE market_signals
                        ADD CONSTRAINT market_signals_vendor_id_fkey
                        FOREIGN KEY (vendor_id)
                        REFERENCES vendors(id)
                        ON DELETE RESTRICT
                """)
                print("  FK RESTRICT recréée")

conn.close()

# Stamp alembic
print("\n=== ALEMBIC STAMP m5_fix_market_signals_vendor_type ===")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
result = subprocess.run(
    ["alembic", "stamp", "m5_fix_market_signals_vendor_type"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=root,
)
stdout = result.stdout.encode("ascii", errors="replace").decode("ascii")
stderr = result.stderr.encode("ascii", errors="replace").decode("ascii")
print("STDOUT:", stdout)
print("STDERR:", stderr)
print("EXIT CODE:", result.returncode)

# Vérification finale
if result.returncode == 0:
    result2 = subprocess.run(
        ["alembic", "heads"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=root,
    )
    heads = result2.stdout.encode("ascii", errors="replace").decode("ascii")
    print("\n=== ALEMBIC HEADS ===")
    print(heads)
