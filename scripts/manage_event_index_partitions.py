"""Manage dms_event_index partitions (semiannual, forward-looking).

Run before each semester in production (or via pg_cron):
  python scripts/manage_event_index_partitions.py

Creates the next N semiannual partitions if they don't exist yet.
Safe to run multiple times (idempotent).
"""

from __future__ import annotations

import os
import sys
from datetime import date

import psycopg
from dotenv import load_dotenv

load_dotenv()

_PARENT_TABLE = "public.dms_event_index"
_SCHEMA = "public"
_LOOKAHEAD_SEMESTERS = 4  # create partitions for the next 2 years


def _semester_range(year: int, half: int) -> tuple[str, str]:
    """Return (start_date, end_date) strings for a semester.

    half=1 → H1 (Jan-Jun), half=2 → H2 (Jul-Dec).
    """
    if half == 1:
        return (f"{year}-01-01", f"{year}-07-01")
    return (f"{year}-07-01", f"{year + 1}-01-01")


def _partition_name(year: int, half: int) -> str:
    return f"dms_event_index_{year}_h{half}"


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    today = date.today()
    current_year = today.year
    current_half = 1 if today.month <= 6 else 2

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            year, half = current_year, current_half
            created = 0
            skipped = 0

            for _ in range(_LOOKAHEAD_SEMESTERS):
                name = _partition_name(year, half)
                start, end = _semester_range(year, half)

                cur.execute(
                    """
                    SELECT 1 FROM pg_inherits i
                    JOIN pg_class p ON p.oid = i.inhparent
                    JOIN pg_class c ON c.oid = i.inhrelid
                    JOIN pg_namespace pn ON pn.oid = p.relnamespace
                    WHERE pn.nspname = %s
                      AND p.relname  = %s
                      AND c.relname  = %s
                    """,
                    ("public", "dms_event_index", name),
                )
                exists = cur.fetchone() is not None

                if exists:
                    print(f"  SKIP  {name} (already exists)")
                    skipped += 1
                else:
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {_SCHEMA}.{name}
                            PARTITION OF {_PARENT_TABLE}
                            FOR VALUES FROM ('{start}') TO ('{end}')
                        """)
                    print(f"  CREATE {name} [{start} → {end})")
                    created += 1

                # Advance to next semester
                if half == 1:
                    half = 2
                else:
                    half = 1
                    year += 1

            conn.commit()

    print(f"\nDone — {created} created, {skipped} skipped.")


if __name__ == "__main__":
    main()
