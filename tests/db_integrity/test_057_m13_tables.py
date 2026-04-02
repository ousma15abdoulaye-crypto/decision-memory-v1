"""Migration 057 / 058 — M13 tables, FK, triggers, indexes (DB required)."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL non défini — tests DB ignorés",
)


class TestM13RegProfileVersions:
    def test_table_exists(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "AND table_name = 'm13_regulatory_profile_versions'"
            )
            assert cur.fetchone() is not None

    def test_unique_index_case_version(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_indexes "
                "WHERE indexname = 'uix_m13_reg_profile_case_version'"
            )
            assert cur.fetchone() is not None

    def test_case_id_fk(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.table_constraints "
                "WHERE table_name = 'm13_regulatory_profile_versions' "
                "AND constraint_type = 'FOREIGN KEY'"
            )
            assert cur.fetchone() is not None


class TestM13CorrectionLog:
    def test_table_exists(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "AND table_name = 'm13_correction_log'"
            )
            assert cur.fetchone() is not None

    def test_case_id_fk(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.table_constraints "
                "WHERE table_name = 'm13_correction_log' "
                "AND constraint_type = 'FOREIGN KEY'"
            )
            assert cur.fetchone() is not None

    def test_append_only_triggers(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT trigger_name FROM information_schema.triggers "
                "WHERE event_object_table = 'm13_correction_log' "
                "ORDER BY trigger_name"
            )
            names = sorted(
                r[0] if isinstance(r, tuple) else r["trigger_name"]
                for r in cur.fetchall()
            )
        assert "trg_m13_correction_log_no_delete" in names
        assert "trg_m13_correction_log_no_update" in names

    def test_case_id_index_058(self, db_conn) -> None:
        """Migration 058 adds an index on case_id for FK join performance."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_indexes "
                "WHERE indexname = 'idx_m13_correction_log_case_id'"
            )
            assert cur.fetchone() is not None
