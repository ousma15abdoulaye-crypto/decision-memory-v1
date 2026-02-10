#!/usr/bin/env python3
"""Smoke test: verify Postgres is reachable and Alembic migration creates all expected tables."""

from __future__ import annotations

import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main() -> None:
    from sqlalchemy import create_engine, inspect, text

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("❌ DATABASE_URL not set")
        sys.exit(1)

    # Alembic / this script need a sync driver
    sync_url = db_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    print(f"Connecting to: {sync_url.split('@')[-1] if '@' in sync_url else sync_url}")

    engine = create_engine(sync_url)

    # 1. Basic connectivity
    with engine.connect() as conn:
        row = conn.execute(text("SELECT 1")).scalar()
        assert row == 1, "SELECT 1 failed"
        print("✅ Postgres connectivity OK")

    # 2. Run Alembic migration
    print("Running alembic upgrade head …")
    import subprocess

    env = {**os.environ, "DATABASE_URL": db_url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=os.path.join(os.path.dirname(__file__), ".."),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"❌ Alembic migration failed:\n{result.stderr}")
        sys.exit(1)
    print("✅ Alembic upgrade head OK")

    # 3. Verify expected tables
    expected_tables = {
        # Couche A
        "cases", "lots", "submissions", "submission_documents",
        "preanalysis_results", "cba_exports", "minutes_pv", "outbox_events",
        # Couche B
        "vendors", "vendor_aliases", "vendor_events",
        "items", "item_aliases",
        "units", "unit_aliases",
        "geo_master", "geo_aliases",
        "market_signals",
        # System
        "audit_log",
    }

    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())
    missing = expected_tables - actual_tables
    if missing:
        print(f"❌ Missing tables: {missing}")
        sys.exit(1)
    print(f"✅ All {len(expected_tables)} expected tables present")

    engine.dispose()
    print("🎉 Smoke test PASSED")


if __name__ == "__main__":
    main()
