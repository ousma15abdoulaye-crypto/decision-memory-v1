"""Fix alembic_version when upgrading from deleted 017 to 018.

Run this if: alembic upgrade head fails with "Can't locate revision 017_merge_heads_caf_016"

Usage: DATABASE_URL=... python scripts/fix_alembic_version_017_to_018.py
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(".env.local")
except ImportError:
    pass

url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not url:
    print("DATABASE_URL required")
    sys.exit(1)

import psycopg

with psycopg.connect(url, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        rows = cur.fetchall()
        if not rows:
            print("alembic_version empty")
            sys.exit(1)
        for row in rows:
            if "017" in str(row[0]):
                cur.execute(
                    "UPDATE alembic_version SET version_num = '018_fix_alembic_heads' WHERE version_num = %s",
                    (row[0],),
                )
                print(f"Updated {row[0]} -> 018_fix_alembic_heads")
            elif "caf949970819" in str(row[0]):
                cur.execute(
                    "UPDATE alembic_version SET version_num = '018_fix_alembic_heads' WHERE version_num = %s",
                    (row[0],),
                )
                print(f"Updated {row[0]} -> 018_fix_alembic_heads")
        print("Done. Run: alembic current")
