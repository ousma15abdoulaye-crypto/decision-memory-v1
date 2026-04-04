"""Tests DB integrity — workspace_events append-only (INV-W03, INV-W05, S12).

Vérifie :
- workspace_events INSERT -> OK
- workspace_events UPDATE -> exception fn_reject_mutation
- workspace_events DELETE -> exception fn_reject_mutation
- workspace_id NOT NULL -> exception sur INSERT sans workspace_id

Pré-condition : migrations 068-069 appliquées (process_workspaces, workspace_events).
"""

from __future__ import annotations

import uuid

import psycopg
import pytest


def _make_tenant_id(cur) -> str:
    cur.execute("SELECT id FROM tenants WHERE code = 'sci_mali' LIMIT 1")
    row = cur.fetchone()
    if row:
        return str(row["id"])
    tid = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s) RETURNING id",
        (tid, "test_tenant_ws", "Test Tenant WS"),
    )
    return str(cur.fetchone()["id"])


def _make_user_id(cur) -> int:
    cur.execute("SELECT id FROM users LIMIT 1")
    row = cur.fetchone()
    if row:
        return int(row["id"])
    cur.execute("""
        INSERT INTO users (email, username, hashed_password, full_name, role_id, created_at)
        VALUES ('ws_test@dms.local', 'ws_test', 'x', 'WS Test', 1, NOW())
        ON CONFLICT (username) DO NOTHING
        RETURNING id
        """)
    row = cur.fetchone()
    return int(row["id"]) if row else 1


def _make_workspace(cur, tenant_id: str, user_id: int) -> str:
    ws_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO process_workspaces
            (id, tenant_id, created_by, reference_code, title, process_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (ws_id, tenant_id, user_id, f"REF-TEST-{ws_id[:8]}", "Test WS", "devis_simple"),
    )
    return ws_id


@pytest.mark.db_integrity
def test_workspace_events_insert_ok(db_conn):
    """Un INSERT valide dans workspace_events doit réussir."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        tenant_id = _make_tenant_id(cur)
        user_id = _make_user_id(cur)
        ws_id = _make_workspace(cur, tenant_id, user_id)

        cur.execute(
            """
            INSERT INTO workspace_events
                (workspace_id, tenant_id, event_type, actor_id, actor_type)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (ws_id, tenant_id, "WORKSPACE_CREATED", user_id, "user"),
        )
        row = cur.fetchone()
        assert row is not None
        assert row["id"] > 0


@pytest.mark.db_integrity
def test_workspace_events_update_rejected(db_conn):
    """UPDATE sur workspace_events doit lever une exception (fn_reject_mutation)."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        tenant_id = _make_tenant_id(cur)
        user_id = _make_user_id(cur)
        ws_id = _make_workspace(cur, tenant_id, user_id)

        cur.execute(
            """
            INSERT INTO workspace_events
                (workspace_id, tenant_id, event_type, actor_id, actor_type)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (ws_id, tenant_id, "WORKSPACE_CREATED", user_id, "user"),
        )
        event_id = cur.fetchone()["id"]

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        with pytest.raises(psycopg.errors.RaiseException):
            cur.execute(
                "UPDATE workspace_events SET payload = '{}' WHERE id = %s",
                (event_id,),
            )


@pytest.mark.db_integrity
def test_workspace_events_delete_rejected(db_conn):
    """DELETE sur workspace_events doit lever une exception (fn_reject_mutation)."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        tenant_id = _make_tenant_id(cur)
        user_id = _make_user_id(cur)
        ws_id = _make_workspace(cur, tenant_id, user_id)

        cur.execute(
            """
            INSERT INTO workspace_events
                (workspace_id, tenant_id, event_type, actor_id, actor_type)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (ws_id, tenant_id, "WORKSPACE_CREATED", user_id, "user"),
        )
        event_id = cur.fetchone()["id"]

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        with pytest.raises(psycopg.errors.RaiseException):
            cur.execute("DELETE FROM workspace_events WHERE id = %s", (event_id,))


@pytest.mark.db_integrity
def test_workspace_events_workspace_id_not_null(db_conn):
    """INSERT workspace_events sans workspace_id doit être rejeté (NOT NULL)."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        tenant_id = _make_tenant_id(cur)
        user_id = _make_user_id(cur)

        with pytest.raises(psycopg.errors.NotNullViolation):
            cur.execute(
                """
                INSERT INTO workspace_events
                    (workspace_id, tenant_id, event_type, actor_id, actor_type)
                VALUES (NULL, %s, %s, %s, %s)
                """,
                (tenant_id, "WORKSPACE_CREATED", user_id, "user"),
            )
