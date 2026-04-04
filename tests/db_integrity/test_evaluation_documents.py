"""Migration 056 + 073/074/076 — evaluation_documents table, FK, RLS, index (DB required)."""

from __future__ import annotations


class TestEvaluationDocuments:
    def test_table_exists(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "AND table_name = 'evaluation_documents'"
            )
            assert cur.fetchone() is not None

    def test_unique_index_workspace_version(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_indexes "
                "WHERE indexname = 'uix_evaluation_documents_workspace_version'"
            )
            assert cur.fetchone() is not None

    def test_workspace_id_fk(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.table_constraints "
                "WHERE table_name = 'evaluation_documents' "
                "AND constraint_type = 'FOREIGN KEY'"
            )
            assert cur.fetchone() is not None

    def test_committee_id_fk(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_name = 'evaluation_documents' "
                "AND constraint_type = 'FOREIGN KEY'"
            )
            rows = cur.fetchall()
            fk_names = [
                r[0] if isinstance(r, tuple) else r["constraint_name"] for r in rows
            ]
            assert (
                len(fk_names) >= 2
            ), "Expected at least 2 FKs (workspace_id, committee_id)"

    def test_rls_enabled(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT relrowsecurity FROM pg_class "
                "WHERE relname = 'evaluation_documents'"
            )
            row = cur.fetchone()
            val = row[0] if isinstance(row, tuple) else row["relrowsecurity"]
            assert val is True

    def test_status_check_constraint(self, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.table_constraints "
                "WHERE table_name = 'evaluation_documents' "
                "AND constraint_type = 'CHECK'"
            )
            assert cur.fetchone() is not None

    def test_columns_exist(self, db_conn) -> None:
        expected = {
            "id",
            "workspace_id",
            "committee_id",
            "version",
            "scores_matrix",
            "justifications",
            "status",
            "created_at",
        }
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "AND table_name = 'evaluation_documents'"
            )
            cols = {
                r[0] if isinstance(r, tuple) else r["column_name"]
                for r in cur.fetchall()
            }
        for col in expected:
            assert col in cols, f"Column {col} missing from evaluation_documents"
