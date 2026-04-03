"""
H0.6 — Probe M13 gates before H1.

3 conditions:
1. evaluation_documents table exists
2. RLS policy covers evaluation_documents
3. FSM accepts Pass 2A (ANNOTATION_USE_PASS_2A env var wiring exists)

Requires DATABASE_URL for conditions 1-2.
Condition 3 checks code presence only (no DB).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _connect():
    import psycopg
    from psycopg.rows import dict_row

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("SKIP: DATABASE_URL not set — conditions 1-2 require DB")
        return None
    clean = url.replace("postgresql+psycopg://", "postgresql://")
    try:
        return psycopg.connect(clean, row_factory=dict_row)
    except Exception as exc:
        print(f"SKIP: Cannot connect — {exc}")
        return None


def check_evaluation_documents_exists(conn) -> bool:
    if conn is None:
        return False
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'evaluation_documents'
            ) AS exists_flag
        """)
        row = cur.fetchone()
        return bool(row and row["exists_flag"])


def check_rls_policy(conn) -> bool:
    if conn is None:
        return False
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS c FROM pg_policies
            WHERE schemaname = 'public'
              AND tablename = 'evaluation_documents'
        """)
        row = cur.fetchone()
        return bool(row and row["c"] > 0)


def check_pass_2a_wiring() -> bool:
    orchestrator = REPO_ROOT / "src" / "annotation" / "orchestrator.py"
    if not orchestrator.exists():
        return False
    content = orchestrator.read_text(encoding="utf-8")
    return "ANNOTATION_USE_PASS_2A" in content


def main() -> None:
    conn = _connect()
    results = {}

    results["evaluation_documents_exists"] = check_evaluation_documents_exists(conn)
    results["rls_policy_exists"] = check_rls_policy(conn)
    results["pass_2a_wiring"] = check_pass_2a_wiring()

    if conn:
        conn.close()

    print("=" * 50)
    print("H0.6 — M13 GATE PROBE")
    print("=" * 50)
    passed = 0
    total = 3
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
        if ok:
            passed += 1

    print(f"\nResult: {passed}/{total}")
    if passed == total:
        print("VERDICT: GATE OPEN — H1 preconditions met")
    else:
        print("VERDICT: GATE BLOCKED — fix failures before H1")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
