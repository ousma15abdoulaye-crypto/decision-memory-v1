#!/usr/bin/env python3
"""V5 fix: Creer un vendor 'mercurials_proxy' et lier les 21850 market_surveys."""

import os
import uuid
from datetime import UTC, datetime

import psycopg

RAILWAY_URL = os.environ.get(
    "RAILWAY_DATABASE_URL",
    "postgresql://postgres:VvIxShbsVuwXdqGlipWTeZjfHKTEbFHP@maglev.proxy.rlwy.net:35451/railway",
)


def main() -> None:
    print("Connecting to Railway...")
    conn = psycopg.connect(RAILWAY_URL, connect_timeout=25)

    with conn.cursor() as cur:
        # Get full schema with NOT NULL info
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='vendors'
            ORDER BY ordinal_position
            """)
        all_cols = cur.fetchall()
        print("=== vendors schema (full) ===")
        required = []
        for c in all_cols:
            flag = " [NOT NULL, NO DEFAULT]" if c[2] == "NO" and not c[3] else ""
            print(f"  {c[0]:30s} {c[1]:25s} nullable={c[2]}{flag}")
            if c[2] == "NO" and not c[3]:
                required.append(c[0])

        print(f"\nRequired (NOT NULL, no default): {required}")

        # Check existing
        cur.execute(
            "SELECT id FROM public.vendors WHERE name_raw=%s LIMIT 1",
            ("mercurials_proxy",),
        )
        existing = cur.fetchone()
        if existing:
            vendor_id = existing[0]
            print(f"\nVendor 'mercurials_proxy' already exists: id={vendor_id}")
        else:
            vendor_id = str(uuid.uuid4())
            now = datetime.now(UTC)
            col_names = [c[0] for c in all_cols]

            # Comprehensive row with all known NOT NULL fields
            row: dict = {}
            if "id" in col_names:
                row["id"] = vendor_id
            if "vendor_id" in col_names:
                # Format: DMS-VND-[A-Z]{3}-[0-9]{4}-[A-Z]
                row["vendor_id"] = "DMS-VND-SYN-0001-A"
            if "fingerprint" in col_names:
                row["fingerprint"] = "mercurials_proxy_synthetic"
            if "name_raw" in col_names:
                row["name_raw"] = "mercurials_proxy"
            if "name_normalized" in col_names:
                row["name_normalized"] = "mercurials_proxy"
            if "canonical_name" in col_names:
                row["canonical_name"] = "mercurials_proxy"
            if "region_code" in col_names:
                # Must be one of: BKO MPT SGO SKS GAO TBK MNK KYS KLK INT
                row["region_code"] = "BKO"
            if "activity_status" in col_names:
                # Must be: VERIFIED_ACTIVE | UNVERIFIED | INACTIVE | GHOST_SUSPECTED
                row["activity_status"] = "UNVERIFIED"
            if "verification_status" in col_names:
                # Must be: registered | qualified | approved | suspended
                row["verification_status"] = "registered"
            if "aliases" in col_names:
                row["aliases"] = []
            if "zones_covered" in col_names:
                row["zones_covered"] = []
            if "category_ids" in col_names:
                row["category_ids"] = []
            if "has_sanctions_cert" in col_names:
                row["has_sanctions_cert"] = False
            if "has_sci_conditions" in col_names:
                row["has_sci_conditions"] = False
            if "key_personnel_verified" in col_names:
                row["key_personnel_verified"] = False
            if "email_verified" in col_names:
                row["email_verified"] = False
            if "is_active" in col_names:
                row["is_active"] = True
            if "source" in col_names:
                row["source"] = "mercurials_proxy"
            if "created_at" in col_names:
                row["created_at"] = now
            if "updated_at" in col_names:
                row["updated_at"] = now

            # Try insert; if still failing, show the constraint details
            cols_sql = ", ".join(row.keys())
            vals_sql = ", ".join(["%s"] * len(row))
            try:
                cur.execute("SAVEPOINT sp_vendor")
                cur.execute(
                    f"INSERT INTO public.vendors ({cols_sql}) VALUES ({vals_sql})",
                    list(row.values()),
                )
                cur.execute("RELEASE SAVEPOINT sp_vendor")
                print(f"\nCreated vendor 'mercurials_proxy': id={vendor_id}")
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sp_vendor")
                print(f"\nERR creating vendor: {e}")
                # Show what columns exist with NOT NULL constraint
                cur.execute("""
                    SELECT c.column_name
                    FROM information_schema.columns c
                    WHERE c.table_schema='public' AND c.table_name='vendors'
                      AND c.is_nullable='NO'
                      AND c.column_default IS NULL
                    ORDER BY c.ordinal_position
                    """)
                print("NOT NULL no-default columns:", [r[0] for r in cur.fetchall()])
                conn.close()
                return

        # Link surveys to vendor
        cur.execute(
            """
            UPDATE public.market_surveys
            SET vendor_id = %s
            WHERE supplier_raw = 'mercurials_proxy' AND vendor_id IS NULL
            """,
            (vendor_id,),
        )
        updated = cur.rowcount
        print(f"Updated {updated} market_surveys rows")

        conn.commit()

        cur.execute(
            "SELECT COUNT(*) FROM public.market_surveys WHERE vendor_id IS NULL"
        )
        remaining = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM public.vendors")
        total_v = cur.fetchone()[0]
        print(f"\nFinal: vendors={total_v}  surveys_without_vendor_id={remaining}")
        print(
            "V5 COMPLETE" if remaining == 0 else f"V5 PARTIAL: {remaining} still NULL"
        )

    conn.close()


if __name__ == "__main__":
    main()
