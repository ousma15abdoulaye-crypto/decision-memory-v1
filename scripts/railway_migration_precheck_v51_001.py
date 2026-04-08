#!/usr/bin/env python3
"""Pré-check DB Railway — mandat DMS-MIGRATION-PROD-V51-001 (Phase 0.3)."""

from __future__ import annotations

import os
import sys

import psycopg


def main() -> int:
    raw = os.environ.get("DATABASE_URL", "")
    if not raw:
        print("DATABASE_URL absent", file=sys.stderr)
        return 1
    u = raw.replace("postgresql+psycopg://", "postgresql://", 1)
    conn = psycopg.connect(u)
    cur = conn.cursor()
    cur.execute("SELECT version()")
    print("PG Version:", cur.fetchone()[0][:60])
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
    )
    print("Tables count:", cur.fetchone()[0])
    cur.execute("SELECT version_num FROM alembic_version")
    row = cur.fetchone()
    print("Alembic version:", row[0] if row else "NONE")
    cur.execute("""
        SELECT count(*) FROM pg_stat_activity
        WHERE state = 'idle in transaction'
          AND now() - query_start > interval '5 minutes'
        """)
    idle_tx = cur.fetchone()[0]
    print("Idle transactions (>5min):", idle_tx)
    cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
    print("Database size:", cur.fetchone()[0])
    conn.close()
    print("---")
    print("Pre-check: OK" if idle_tx == 0 else "Pre-check: WARNING — idle transactions")
    return 0 if idle_tx == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
