"""Pre-flight probe for M9 migration — checks required tables/views/triggers.

Usage:
    DATABASE_URL=postgresql://user:pass@host/dbname python scripts/_probe_m9.py
"""
import os
import sys
import psycopg
from psycopg.rows import dict_row

_raw = os.environ.get("DATABASE_URL")
if not _raw:
    print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
    sys.exit(1)

# SQLAlchemy prefix -> psycopg native
if _raw.startswith("postgresql+psycopg://"):
    url = _raw.replace("postgresql+psycopg://", "postgresql://", 1)
else:
    url = _raw

tables_needed = [
    "score_runs",
    "cases",
    "committee_events",
    "decision_snapshots",
    "scoring_meta",
    "corrections",
    "suppliers",
    "proposals",
]
views_needed = ["current_supplier_scores"]
triggers_needed = ["trg_score_runs_append_only", "trg_corrections_append_only"]
cols_check = [
    ("cases", "currency"),
]

# Tables/views/triggers that M9 must CREATE (must NOT exist yet)
m9_must_not_exist_tables = ["committee_events", "decision_snapshots"]
m9_must_not_exist_triggers = [
    "trg_committee_events_append_only",
    "trg_decision_snapshots_append_only",
    "trg_committee_smart_lock",
]

with psycopg.connect(url, row_factory=dict_row) as conn:
    cur = conn.cursor()

    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    existing_tables = {r["tablename"] for r in cur.fetchall()}

    cur.execute("SELECT viewname FROM pg_views WHERE schemaname='public'")
    existing_views = {r["viewname"] for r in cur.fetchall()}

    cur.execute(
        "SELECT trigger_name FROM information_schema.triggers WHERE trigger_schema='public'"
    )
    existing_triggers = {r["trigger_name"] for r in cur.fetchall()}

    print("\n--- 0-C TABLES (pre-M9) ---")
    for t in tables_needed:
        status = "OK" if t in existing_tables else "MISSING"
        print(f"  {status}  {t}")

    print("\n--- 0-C VIEWS ---")
    for v in views_needed:
        status = "OK" if v in existing_views else "MISSING"
        print(f"  {status}  {v}")

    print("\n--- 0-C TRIGGERS ---")
    for tg in triggers_needed:
        status = "OK" if tg in existing_triggers else "MISSING"
        print(f"  {status}  {tg}")

    print("\n--- 0-C COLUMNS ---")
    for tbl, col in cols_check:
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s AND column_name=%s",
            (tbl, col),
        )
        status = "OK" if cur.fetchone() else "MISSING"
        print(f"  {status}  {tbl}.{col}")

    print("\n--- 0-D M9 TARGETS (must NOT exist yet) ---")
    for t in m9_must_not_exist_tables:
        status = "ABSENT (OK)" if t not in existing_tables else "ALREADY EXISTS (check)"
        print(f"  {status}  table:{t}")
    for tg in m9_must_not_exist_triggers:
        status = (
            "ABSENT (OK)" if tg not in existing_triggers else "ALREADY EXISTS (check)"
        )
        print(f"  {status}  trigger:{tg}")

    # 0-E: alembic versions present
    print("\n--- 0-E ALEMBIC versions ---")
    cur.execute("SELECT version_num FROM alembic_version")
    for r in cur.fetchall():
        print(f"  current head: {r['version_num']}")

    # 0-F: scoring_meta rows
    print("\n--- 0-F scoring_meta sample ---")
    try:
        cur.execute("SELECT * FROM scoring_meta ORDER BY created_at DESC LIMIT 3")
        rows = cur.fetchall()
        if rows:
            for r in rows:
                print(f"  {r}")
        else:
            print("  (empty)")
    except Exception as e:
        print(f"  ERROR: {e}")

    # 0-G: score_runs count
    print("\n--- 0-G score_runs count ---")
    try:
        cur.execute("SELECT COUNT(*) AS cnt FROM score_runs")
        print(f"  count={cur.fetchone()['cnt']}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\nPre-flight M9 done.")
