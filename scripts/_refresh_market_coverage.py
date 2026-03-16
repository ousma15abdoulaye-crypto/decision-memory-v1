#!/usr/bin/env python3
"""Refresh market_coverage CONCURRENTLY."""
import os
try:
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg

db = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not db:
    raise SystemExit("DATABASE_URL absente")
conn = psycopg.connect(db)
conn.autocommit = True
conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY public.market_coverage")
conn.close()
print("REFRESH MATERIALIZED VIEW CONCURRENTLY market_coverage OK")
