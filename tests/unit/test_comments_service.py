"""Tests unitaires — comments_service (add_smart_comment, INV-S04).

Canon V5.1.0 Section O8 (CDE) + INV-S04.
Locking tests 7 (INV-S03) et 8 (INV-S04) — aspects comportementaux côté service.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestInferCommentType:
    def test_flag_always_returns_flag(self):
        from src.services.comments_service import _infer_comment_type

        assert _infer_comment_type("Good service", is_flag=True) == "flag"

    def test_question_mark_returns_question(self):
        from src.services.comments_service import _infer_comment_type

        assert _infer_comment_type("Quel est le délai?", is_flag=False) == "question"

    def test_question_mark_trailing_space(self):
        from src.services.comments_service import _infer_comment_type

        assert _infer_comment_type("Prix trop élevé ? ", is_flag=False) == "question"

    def test_plain_comment(self):
        from src.services.comments_service import _infer_comment_type

        assert _infer_comment_type("Bon fournisseur.", is_flag=False) == "comment"

    def test_empty_string_returns_comment(self):
        from src.services.comments_service import _infer_comment_type

        assert _infer_comment_type("", is_flag=False) == "comment"

    def test_flag_overrides_question_mark(self):
        from src.services.comments_service import _infer_comment_type

        assert _infer_comment_type("Vraiment?", is_flag=True) == "flag"


class TestAddSmartComment:
    """Vérifie le comportement de add_smart_comment avec DB mock."""

    def _make_conn(
        self,
        *,
        thread_id: str = "thread-001",
        message_id: str = "msg-001",
        comment_id: str = "cmt-001",
        existing_thread: dict | None = None,
    ):
        conn = MagicMock()
        call_count = {"n": 0}

        def fake_execute_one(conn_, sql, params):
            call_count["n"] += 1
            sql_strip = sql.strip().upper()
            if sql_strip.startswith("SELECT") and "DELIBERATION_THREADS" in sql_strip:
                return existing_thread
            if sql_strip.startswith("INSERT INTO DELIBERATION_THREADS"):
                return {"id": thread_id}
            if sql_strip.startswith("INSERT INTO DELIBERATION_MESSAGES"):
                return {"id": message_id}
            if sql_strip.startswith("INSERT INTO ASSESSMENT_COMMENTS"):
                return {"id": comment_id}
            if sql_strip.startswith("INSERT INTO ASSESSMENT_HISTORY"):
                return None
            return None

        return conn, fake_execute_one

    def test_add_comment_creates_thread_and_stores(self):
        from src.services.comments_service import add_smart_comment

        conn, fake_exe = self._make_conn(
            thread_id="th-1", message_id="m-1", comment_id="c-1"
        )
        with patch("src.services.comments_service.db_execute_one", fake_exe):
            result = add_smart_comment(
                conn,
                workspace_id="ws-001",
                tenant_id="t-001",
                author_user_id=42,
                content="Le délai est court.",
            )
        assert result["comment_id"] == "c-1"
        assert result["message_id"] == "m-1"
        assert result["thread_id"] == "th-1"
        assert result["comment_type"] == "comment"
        assert result["is_flag"] is False

    def test_add_flag_infers_flag_type(self):
        from src.services.comments_service import add_smart_comment

        conn, fake_exe = self._make_conn(
            thread_id="th-2", message_id="m-2", comment_id="c-2"
        )
        with patch("src.services.comments_service.db_execute_one", fake_exe):
            result = add_smart_comment(
                conn,
                workspace_id="ws-001",
                tenant_id="t-001",
                author_user_id=42,
                content="Suspicion de surfacturation.",
                is_flag=True,
                criterion_assessment_id="ca-001",
            )
        assert result["comment_type"] == "flag"
        assert result["is_flag"] is True

    def test_add_question_infers_question_type(self):
        from src.services.comments_service import add_smart_comment

        conn, fake_exe = self._make_conn(
            thread_id="th-3", message_id="m-3", comment_id="c-3"
        )
        with patch("src.services.comments_service.db_execute_one", fake_exe):
            result = add_smart_comment(
                conn,
                workspace_id="ws-001",
                tenant_id="t-001",
                author_user_id=42,
                content="Est-ce que le prix inclut la TVA?",
            )
        assert result["comment_type"] == "question"

    def test_empty_content_raises(self):
        import pytest

        from src.services.comments_service import add_smart_comment

        conn = MagicMock()
        with pytest.raises(ValueError, match="vide"):
            add_smart_comment(
                conn,
                workspace_id="ws-001",
                tenant_id="t-001",
                author_user_id=42,
                content="",
            )

    def test_reuse_existing_thread(self):
        from src.services.comments_service import add_smart_comment

        existing_thread = {"id": "existing-thread"}
        conn, fake_exe = self._make_conn(
            thread_id="new-thread",
            message_id="m-x",
            comment_id="c-x",
            existing_thread=existing_thread,
        )
        with patch("src.services.comments_service.db_execute_one", fake_exe):
            result = add_smart_comment(
                conn,
                workspace_id="ws-001",
                tenant_id="t-001",
                author_user_id=42,
                content="Complément d'info.",
                criterion_assessment_id="ca-002",
            )
        assert result["thread_id"] == "existing-thread"

    def test_explicit_thread_id_bypasses_lookup(self):
        from src.services.comments_service import add_smart_comment

        call_log = []

        def fake_exe(conn_, sql, params):
            call_log.append(sql.strip().upper()[:40])
            if "INSERT INTO DELIBERATION_MESSAGES" in sql.upper():
                return {"id": "msg-explicit"}
            if "INSERT INTO ASSESSMENT_COMMENTS" in sql.upper():
                return {"id": "cmt-explicit"}
            return None

        conn = MagicMock()
        with patch("src.services.comments_service.db_execute_one", fake_exe):
            result = add_smart_comment(
                conn,
                workspace_id="ws-001",
                tenant_id="t-001",
                author_user_id=42,
                content="Remarque.",
                thread_id="given-thread",
            )
        assert result["thread_id"] == "given-thread"
        assert not any(
            "SELECT" in c for c in call_log
        ), "Ne doit pas chercher de thread"
