"""Migration 059 — score_history + elimination_log (RLS, append-only triggers)."""

from __future__ import annotations

import pytest


def _table_exists(db_conn, name: str) -> bool:
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (name,),
        )
        return cur.fetchone() is not None


class TestM14AuditTables:
    def test_tables_exist(self, db_conn) -> None:
        if not _table_exists(db_conn, "score_history"):
            pytest.skip("migration 059 non appliquée — alembic upgrade head")
        assert _table_exists(db_conn, "elimination_log")

    def test_score_history_rls(self, db_conn) -> None:
        if not _table_exists(db_conn, "score_history"):
            pytest.skip("migration 059 non appliquée")
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT relrowsecurity FROM pg_class WHERE relname = 'score_history'"
            )
            row = cur.fetchone()
            val = row[0] if isinstance(row, tuple) else row["relrowsecurity"]
            assert val is True

    def test_score_history_append_only(self, db_conn) -> None:
        if not _table_exists(db_conn, "score_history"):
            pytest.skip("migration 059 non appliquée")

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT id::text FROM public.process_workspaces LIMIT 1",
            )
            row = cur.fetchone()
            if row is None:
                pytest.skip("aucun process_workspace en base")
            workspace_id = row[0] if isinstance(row, tuple) else row["id"]
            # RLS FORCE : même superuser — aligner le test sur le trigger append-only
            cur.execute("SELECT set_config('app.is_admin', 'true', true)")
            cur.execute(
                """
                INSERT INTO public.score_history (
                    workspace_id, offer_document_id, criterion_key,
                    score_value, max_score, confidence, evidence
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (workspace_id, "m14-audit-test-offer", "crit_x", 1.0, 10.0, 0.6, "t"),
            )
            rid = cur.fetchone()
            pk = rid[0] if isinstance(rid, tuple) else rid["id"]
        with pytest.raises(Exception) as exc:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.is_admin', 'true', true)")
                cur.execute(
                    "UPDATE public.score_history SET confidence = 1.0 WHERE id = %s",
                    (pk,),
                )
        assert (
            "append-only" in str(exc.value).lower()
            or "mutation" in str(exc.value).lower()
        )

    def test_elimination_log_append_only(self, db_conn) -> None:
        if not _table_exists(db_conn, "elimination_log"):
            pytest.skip("migration 059 non appliquée")
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT id::text FROM public.process_workspaces LIMIT 1",
            )
            row = cur.fetchone()
            if row is None:
                pytest.skip("aucun process_workspace en base")
            workspace_id = row[0] if isinstance(row, tuple) else row["id"]
            cur.execute("SELECT set_config('app.is_admin', 'true', true)")
            cur.execute(
                """
                INSERT INTO public.elimination_log (
                    workspace_id, offer_document_id, check_id, check_name, reason
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (workspace_id, "m14-elim-test", "T1", "test", "reason"),
            )
            rid = cur.fetchone()
            pk = rid[0] if isinstance(rid, tuple) else rid["id"]
        with pytest.raises(Exception) as exc:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.is_admin', 'true', true)")
                cur.execute(
                    "DELETE FROM public.elimination_log WHERE id = %s",
                    (pk,),
                )
        assert (
            "append-only" in str(exc.value).lower()
            or "mutation" in str(exc.value).lower()
        )
