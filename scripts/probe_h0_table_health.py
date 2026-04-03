"""
H0.5 — Probe table health for semi-active tables.

Checks decision_snapshots, analysis_summaries, memory_entries for:
- Row counts
- Missing critical fields (case_id, pipeline_run_id)
- Last write timestamp
- Orphaned rows

Outputs a structured report to stdout.  Requires DATABASE_URL.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

OK = "OK"
WARN = "WARN"
EMPTY = "EMPTY"


def _connect():
    import psycopg
    from psycopg.rows import dict_row

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    clean = url.replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(clean, row_factory=dict_row)


def _query(conn, sql: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def _scalar(conn, sql: str):
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
        return list(row.values())[0] if row else None


def probe_decision_snapshots(conn) -> dict:
    total = _scalar(conn, "SELECT COUNT(*) FROM public.decision_snapshots")
    if total == 0:
        return {"table": "decision_snapshots", "status": EMPTY, "count": 0}
    without_case = _scalar(
        conn,
        "SELECT COUNT(*) FROM public.decision_snapshots WHERE case_id IS NULL",
    )
    last_write = _scalar(
        conn,
        "SELECT MAX(created_at) FROM public.decision_snapshots",
    )
    return {
        "table": "decision_snapshots",
        "status": WARN if without_case > 0 else OK,
        "count": total,
        "without_case_id": without_case,
        "last_write": str(last_write) if last_write else None,
    }


def probe_analysis_summaries(conn) -> dict:
    total = _scalar(conn, "SELECT COUNT(*) FROM public.analysis_summaries")
    if total == 0:
        return {"table": "analysis_summaries", "status": EMPTY, "count": 0}
    without_pipeline = _scalar(
        conn,
        "SELECT COUNT(*) FROM public.analysis_summaries WHERE pipeline_run_id IS NULL",
    )
    orphaned = _scalar(
        conn,
        """
        SELECT COUNT(*) FROM public.analysis_summaries a
        WHERE a.pipeline_run_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM public.pipeline_runs p
            WHERE p.pipeline_run_id = a.pipeline_run_id
          )
        """,
    )
    return {
        "table": "analysis_summaries",
        "status": WARN if (without_pipeline or 0) > 0 else OK,
        "count": total,
        "without_pipeline_run_id": without_pipeline,
        "orphaned_pipeline_refs": orphaned,
    }


def probe_memory_entries(conn) -> dict:
    total = _scalar(conn, "SELECT COUNT(*) FROM public.memory_entries")
    if total == 0:
        return {"table": "memory_entries", "status": EMPTY, "count": 0}
    last_write = _scalar(
        conn,
        "SELECT MAX(created_at) FROM public.memory_entries",
    )
    by_type = _query(
        conn,
        "SELECT entry_type, COUNT(*) AS c FROM public.memory_entries GROUP BY entry_type",
    )
    return {
        "table": "memory_entries",
        "status": OK,
        "count": total,
        "last_write": str(last_write) if last_write else None,
        "by_entry_type": {r["entry_type"]: r["c"] for r in by_type},
    }


def main() -> None:
    conn = _connect()
    results = []
    for probe_fn in [probe_decision_snapshots, probe_analysis_summaries, probe_memory_entries]:
        try:
            results.append(probe_fn(conn))
        except Exception as exc:
            results.append({"table": probe_fn.__name__, "status": "ERROR", "error": str(exc)})
    conn.close()

    print("=" * 60)
    print("H0.5 — TABLE HEALTH PROBE")
    print(f"Date: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)
    for r in results:
        print(json.dumps(r, indent=2, default=str))
        print("-" * 40)

    statuses = [r["status"] for r in results]
    if "ERROR" in statuses:
        print("\nVERDICT: ERROR — some probes failed")
        sys.exit(2)
    elif "WARN" in statuses:
        print("\nVERDICT: WARN — anomalies detected, see report")
        sys.exit(0)
    elif all(s == EMPTY for s in statuses):
        print("\nVERDICT: EMPTY — all tables empty (fresh DB or no pipeline runs)")
        sys.exit(0)
    else:
        print("\nVERDICT: OK — all tables healthy")
        sys.exit(0)


if __name__ == "__main__":
    main()
