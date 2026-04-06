"""Threads / messages M16 — délibération contradictoire."""

from __future__ import annotations

from typing import Any

from src.db import db_execute_one, db_fetchall


def get_thread(conn: Any, workspace_id: str, thread_id: str) -> dict[str, Any] | None:
    return db_execute_one(
        conn,
        """
        SELECT id::text AS id, workspace_id::text AS workspace_id,
               committee_session_id::text AS committee_session_id,
               title, thread_status
        FROM deliberation_threads
        WHERE id = CAST(:tid AS uuid)
          AND workspace_id = CAST(:wid AS uuid)
        """,
        {"tid": thread_id, "wid": workspace_id},
    )


def list_threads(conn: Any, workspace_id: str) -> list[dict[str, Any]]:
    return db_fetchall(
        conn,
        """
        SELECT id::text AS id, workspace_id::text AS workspace_id,
               committee_session_id::text AS committee_session_id,
               title, thread_status
        FROM deliberation_threads
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY created_at DESC
        """,
        {"wid": workspace_id},
    )


def insert_thread(
    conn: Any,
    *,
    workspace_id: str,
    tenant_id: str,
    title: str,
    committee_session_id: str | None,
) -> str:
    row = db_execute_one(
        conn,
        """
        INSERT INTO deliberation_threads (
            workspace_id, tenant_id, committee_session_id, title
        )
        VALUES (
            CAST(:wid AS uuid),
            CAST(:tid AS uuid),
            :sid,
            :title
        )
        RETURNING id::text AS id
        """,
        {
            "wid": workspace_id,
            "tid": tenant_id,
            "sid": committee_session_id,
            "title": title,
        },
    )
    if not row or not row.get("id"):
        raise RuntimeError("insert deliberation_threads failed")
    return str(row["id"])


def list_messages(conn: Any, thread_id: str) -> list[dict[str, Any]]:
    return db_fetchall(
        conn,
        """
        SELECT id::text AS id, thread_id::text AS thread_id,
               author_user_id, body, created_at
        FROM deliberation_messages
        WHERE thread_id = CAST(:tid AS uuid)
        ORDER BY created_at, id
        """,
        {"tid": thread_id},
    )


def insert_message(
    conn: Any,
    *,
    thread_id: str,
    workspace_id: str,
    tenant_id: str,
    author_user_id: int,
    body: str,
) -> str:
    row = db_execute_one(
        conn,
        """
        INSERT INTO deliberation_messages (
            thread_id, workspace_id, tenant_id, author_user_id, body
        )
        VALUES (
            CAST(:tid AS uuid),
            CAST(:wid AS uuid),
            CAST(:tenant AS uuid),
            :uid,
            :body
        )
        RETURNING id::text AS id
        """,
        {
            "tid": thread_id,
            "wid": workspace_id,
            "tenant": tenant_id,
            "uid": author_user_id,
            "body": body,
        },
    )
    if not row or not row.get("id"):
        raise RuntimeError("insert deliberation_messages failed")
    return str(row["id"])
