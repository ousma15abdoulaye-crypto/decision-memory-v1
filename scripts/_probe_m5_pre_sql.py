"""Probes SQL A-E pour M5-PRE-HARDENING."""
import os
import psycopg
from psycopg.rows import dict_row

url = os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url = "postgresql://" + url[len("postgres://"):]
url = url.replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:

        # Probe A
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'market_signals' ORDER BY ordinal_position"
        )
        ms_cols = [r["column_name"] for r in cur.fetchall()]
        print("=== PROBE A - market_signals columns ===")
        print(ms_cols if ms_cols else "TABLE ABSENTE OU VIDE")

        # Probe B
        print("\n=== PROBE B - vendors/vendor_identities ===")
        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_name='vendors') AS v"
        )
        vendors_exists = cur.fetchone()["v"]
        print(f"vendors_exists: {vendors_exists}")

        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_name='vendor_identities') AS v"
        )
        vi_exists = cur.fetchone()["v"]
        print(f"vendor_identities_exists: {vi_exists}")

        if vendors_exists:
            cur.execute("SELECT COUNT(*) AS n FROM vendors")
            print(f"vendors COUNT: {cur.fetchone()['n']}")
            cur.execute("SELECT * FROM vendors LIMIT 5")
            rows = cur.fetchall()
            print(f"vendors sample ({len(rows)} rows): {[dict(r) for r in rows]}")
        if vi_exists:
            cur.execute("SELECT COUNT(*) AS n FROM vendor_identities")
            print(f"vendor_identities COUNT: {cur.fetchone()['n']}")

        # Probe C
        print("\n=== PROBE C - FK dependencies toward vendors/vendor_identities ===")
        cur.execute(
            """
            SELECT tc.constraint_name, tc.table_name, kcu.column_name,
                   ccu.table_name AS foreign_table, ccu.column_name AS foreign_column
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_name IN ('vendors', 'vendor_identities')
            ORDER BY tc.table_name, tc.constraint_name
            """
        )
        fks = cur.fetchall()
        print(f"FK count toward vendors/vendor_identities: {len(fks)}")
        for fk in fks:
            print(" ", dict(fk))

        # Probe D
        print("\n=== PROBE D - constraints on vendor_identities ===")
        if vi_exists:
            cur.execute(
                "SELECT conname, contype FROM pg_constraint "
                "WHERE conrelid = 'vendor_identities'::regclass ORDER BY conname"
            )
            for r in cur.fetchall():
                print(" ", dict(r))
        else:
            print("  vendor_identities absent - skip")

        # Probe E
        print("\n=== PROBE E - indexes vendors + vendor_identities ===")
        cur.execute(
            "SELECT indexname, tablename FROM pg_indexes "
            "WHERE tablename IN ('vendors','vendor_identities') "
            "ORDER BY tablename, indexname"
        )
        for r in cur.fetchall():
            print(" ", dict(r))
