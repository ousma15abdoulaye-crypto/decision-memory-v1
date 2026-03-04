"""Restaure la DB locale à l'état m5_pre_vendors_consolidation post-downgrade."""
import os
import psycopg

url = os.environ.get("DATABASE_URL", "postgresql+psycopg://dms:dms123@localhost:5432/dms")
url = url.replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ('vendors', 'vendor_identities')
        """)
        tables = [r[0] for r in cur.fetchall()]
        print(f"Tables présentes: {tables}")

        if 'vendor_identities' in tables and 'vendors' not in tables:
            cur.execute("ALTER TABLE vendor_identities RENAME TO vendors")
            print("Renamed vendor_identities → vendors (restauration post-downgrade)")
        elif 'vendors' in tables and 'vendor_identities' not in tables:
            print("Déjà en état post-consolidation (vendors présent, vendor_identities absent) — rien à faire")
        else:
            print(f"État inattendu — tables: {tables}")

print("Done.")
