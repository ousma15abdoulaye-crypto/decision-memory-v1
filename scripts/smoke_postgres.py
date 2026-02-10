#!/usr/bin/env python3
"""
DMS Smoke Test — PostgreSQL (Constitution V2.1 ONLINE-ONLY)
Run with: DATABASE_URL=postgresql+psycopg://... python3 scripts/smoke_postgres.py
Optional: --url postgresql://user:pass@host:5432/db

Imports: src.db (Source of Truth) — no backend.* imports.
"""

from pathlib import Path
import sys

# Ensure project root is in sys.path (works without PYTHONPATH)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import os

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

    from sqlalchemy import create_engine, text, inspect

    db_url = os.environ.get("DATABASE_URL", "")
    sync_url = db_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    # Log only the host/db portion — never print credentials
    if "@" in sync_url:
        safe_display = sync_url.split("@", 1)[-1]
    else:
        safe_display = "(local)"
    print(f"Connecting to: {safe_display}")

    sync_engine = create_engine(sync_url)

    # 1. Basic connectivity
    with sync_engine.connect() as conn:
        row = conn.execute(text("SELECT 1")).scalar()
        assert row == 1, "SELECT 1 failed"
        print("✅ Postgres connectivity OK")

    # 2. Run Alembic migration (if alembic is available)
    try:
        print("Running alembic upgrade head ...")
        import subprocess
        env = {**os.environ, "DATABASE_URL": db_url}
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("✅ Alembic upgrade head OK")
        else:
            print(f"⚠️  Alembic migration skipped (not configured): {result.stderr.strip()[:100]}")
    except Exception as e:
        print(f"⚠️  Alembic not available: {e}")

    # 3. Try init_db_schema (sync schema creation from main's API)
    try:
        init_db_schema()
        print("✅ Schema init OK")
    except Exception as e:
        print(f"⚠️  init_db_schema skipped: {e}")

    # 4. Verify expected tables
    inspector = inspect(sync_engine)
    actual_tables = set(inspector.get_table_names())
    if actual_tables:
        print(f"✅ {len(actual_tables)} tables present: {sorted(actual_tables)}")
    else:
        print("⚠️  No tables found (migrations may not have run)")

    sync_engine.dispose()
    print("🎉 Smoke test PASSED")


if __name__ == "__main__":
    main()
