#!/usr/bin/env python3
"""Post-check Railway — mandat DMS-MIGRATION-PROD-V51-001 (Phase 3 ciblé)."""

from __future__ import annotations

import os

import psycopg


def _url() -> str:
    raw = os.environ.get("DATABASE_URL", "")
    return raw.replace("postgresql+psycopg://", "postgresql://", 1)


def main() -> int:
    conn = psycopg.connect(_url())
    cur = conn.cursor()
    cur.execute("SELECT version_num FROM alembic_version")
    print("alembic_version:", cur.fetchone()[0])

    m16_tables = [
        "evaluation_domains",
        "criterion_assessments",
        "deliberation_threads",
        "deliberation_messages",
        "validated_analytical_notes",
        "criterion_assessment_history",
        "clarification_requests",
        "price_line_comparisons",
        "price_line_bundle_values",
    ]
    print("\n=== Tables M16 (exist) ===")
    for table in m16_tables:
        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = %s
            )
            """,
            (table,),
        )
        ok = cur.fetchone()[0]
        print(f"  {table}: {'OK' if ok else 'MISSING'}")

    print("\n=== RLS FORCED (M16 + V5.1 cibles) ===")
    for table in m16_tables + ["mql_query_log", "assessment_comments"]:
        cur.execute(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = %s AND c.relkind = 'r'",
            (table,),
        )
        row = cur.fetchone()
        if not row:
            print(f"  {table}: NOT FOUND")
            continue
        en, fo = row
        print(f"  {table}: enabled={en} forced={fo}")

    cur.execute("SELECT COUNT(*) FROM criterion_assessments")
    print("\ncriterion_assessments rows:", cur.fetchone()[0])

    cur.execute("""
        SELECT trigger_name FROM information_schema.triggers
        WHERE event_object_table IN ('deliberation_messages', 'assessment_comments')
        ORDER BY event_object_table, trigger_name
        """)
    print("\n=== Triggers (messages / comments) ===")
    for (name,) in cur.fetchall():
        print(f"  {name}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
