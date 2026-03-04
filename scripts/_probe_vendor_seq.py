"""Probe sequences et contrainte chk_vendor_id_format."""
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg, psycopg.rows

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row)
conn.autocommit = True

with conn.cursor() as cur:
    # Toutes les séquences
    cur.execute("SELECT sequencename, last_value FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename")
    seqs = cur.fetchall()
    print("=== SEQUENCES ===")
    for s in seqs:
        print(f"  {s['sequencename']} = {s['last_value']}")

    # Contrainte chk_vendor_id_format
    cur.execute("""
        SELECT pg_get_constraintdef(oid) AS def
        FROM pg_constraint
        WHERE conname = 'chk_vendor_id_format'
          AND conrelid = 'vendors'::regclass
    """)
    r = cur.fetchone()
    print(f"\n=== chk_vendor_id_format ===")
    if r: print(f"  {r['def']}")
    else: print("  ABSENTE")

    # Vendor_id max actuel
    cur.execute("SELECT vendor_id FROM vendors ORDER BY created_at DESC LIMIT 5")
    rows = cur.fetchall()
    print("\n=== vendors récents ===")
    for r in rows: print(f"  {r['vendor_id']}")

conn.close()
