"""Probe triggers M10B — ÉTAPE B CTO."""
import os
import sys

try:
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

import psycopg

db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    print("STOP - DATABASE_URL absente")
    sys.exit(1)
if "://" in db_url:
    scheme_part, rest = db_url.split("://", 1)
    db_url = f"{scheme_part.split('+')[0]}://{rest}"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

conn = psycopg.connect(db_url)
cur = conn.cursor()
cur.execute("""
    SELECT trigger_name, event_object_schema,
           event_object_table, action_timing
    FROM information_schema.triggers
    WHERE trigger_name LIKE %s
    OR    trigger_name LIKE %s
    OR    trigger_name LIKE %s
    ORDER BY trigger_name
""", ("%notify%", "%runs%", "%agent%"))
for r in cur.fetchall():
    print(r)
conn.close()
