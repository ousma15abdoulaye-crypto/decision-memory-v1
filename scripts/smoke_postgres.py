#!/usr/bin/env python3
"""
DMS Smoke Test — PostgreSQL (Constitution V2.1 ONLINE-ONLY)
Run with: DATABASE_URL=postgresql+psycopg://... python3 scripts/smoke_postgres.py
Optional: --url postgresql://user:pass@host:5432/db
"""
from __future__ import annotations

from pathlib import Path
import argparse
import os
import sys

# Ensure project root is in sys.path (works without PYTHONPATH)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Override DATABASE_URL (optional)")
    args = parser.parse_args()
    
    if args.url:
        os.environ["DATABASE_URL"] = args.url
    elif not os.environ.get("DATABASE_URL", "").strip():
        print("ERROR: DATABASE_URL is required. DMS is online-only (Constitution V2.1).", file=sys.stderr)
        print("Usage: DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db python3 scripts/smoke_postgres.py", file=sys.stderr)
        sys.exit(1)

    try:
        from src.db import engine, init_db_schema
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Database URL: {engine.url}")
    print(f"Dialect: {engine.dialect.name}")

    if engine.dialect.name != "postgresql":
        print("ERROR: Expected dialect=postgresql", file=sys.stderr)
        sys.exit(1)

    init_db_schema()
    print("Schema OK")

    with engine.connect() as conn:
        from sqlalchemy import text
        r = conn.execute(text("SELECT 1 AS one")).fetchone()
        assert r[0] == 1
    print("Placeholder transform OK (SELECT 1)")

    print("Smoke test PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
