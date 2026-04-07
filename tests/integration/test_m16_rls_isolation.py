"""F3 — RLS FORCE sur tables M16 (086)."""

from __future__ import annotations

import pytest

M16_TABLES = (
    "evaluation_domains",
    "criterion_assessments",
    "deliberation_threads",
    "deliberation_messages",
    "clarification_requests",
    "criterion_assessment_history",
    "validated_analytical_notes",
    "price_line_comparisons",
    "price_line_bundle_values",
)


@pytest.mark.integration
def test_rls_forced_on_all_m16_tables(db_conn) -> None:
    with db_conn.cursor() as cur:
        for table in M16_TABLES:
            cur.execute(
                """
                SELECT c.relforcerowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = %s
                """,
                (table,),
            )
            row = cur.fetchone()
            assert row is not None, f"table {table} missing"
            assert row["relforcerowsecurity"] is True, f"RLS not FORCED on {table}"
