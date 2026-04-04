"""Tests DB integrity — workspace FSM sealed irreversible (INV-W04, S7).

Vérifie :
- process_workspaces : sealed -> draft -> EXCEPTION trigger
- process_workspaces : sealed -> closed -> OK
- process_workspaces : closed -> sealed -> EXCEPTION trigger
- committee_sessions : sealed -> draft -> EXCEPTION
- committee_sessions : sealed -> closed -> OK

Pré-condition : migrations 068-071 appliquées.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest


def _setup_workspace(cur) -> tuple[str, str, int]:
    cur.execute("SELECT set_config('app.is_admin', 'true', true)")

    cur.execute("SELECT id FROM tenants WHERE code = 'sci_mali' LIMIT 1")
    row = cur.fetchone()
    tenant_id = str(row["id"]) if row else str(uuid.uuid4())
    if not row:
        cur.execute(
            "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s)",
            (tenant_id, "sci_mali_seal", "SCI Mali Seal Test"),
        )

    cur.execute("SELECT id FROM users LIMIT 1")
    row = cur.fetchone()
    user_id = int(row["id"]) if row else 1

    ws_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO process_workspaces
            (id, tenant_id, created_by, reference_code, title, process_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (ws_id, tenant_id, user_id, f"SEAL-{ws_id[:8]}", "Seal Test", "devis_formel"),
    )
    return ws_id, tenant_id, user_id


@pytest.mark.db_integrity
def test_workspace_sealed_to_draft_rejected(db_conn):
    """sealed -> draft doit lever une exception (fn_workspace_sealed_final)."""
    with db_conn.cursor() as cur:
        ws_id, _, _ = _setup_workspace(cur)
        cur.execute(
            "UPDATE process_workspaces SET status = 'sealed' WHERE id = %s",
            (ws_id,),
        )

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        with pytest.raises(psycopg.errors.RaiseException):
            cur.execute(
                "UPDATE process_workspaces SET status = 'draft' WHERE id = %s",
                (ws_id,),
            )


@pytest.mark.db_integrity
def test_workspace_sealed_to_closed_ok(db_conn):
    """sealed -> closed doit réussir (transition légale)."""
    with db_conn.cursor() as cur:
        ws_id, _, _ = _setup_workspace(cur)
        cur.execute(
            "UPDATE process_workspaces SET status = 'sealed' WHERE id = %s",
            (ws_id,),
        )

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            "UPDATE process_workspaces SET status = 'closed' WHERE id = %s",
            (ws_id,),
        )
        cur.execute("SELECT status FROM process_workspaces WHERE id = %s", (ws_id,))
        row = cur.fetchone()
        assert row["status"] == "closed"


@pytest.mark.db_integrity
def test_workspace_closed_to_sealed_rejected(db_conn):
    """closed -> sealed doit lever une exception."""
    with db_conn.cursor() as cur:
        ws_id, _, _ = _setup_workspace(cur)
        cur.execute(
            "UPDATE process_workspaces SET status = 'sealed' WHERE id = %s",
            (ws_id,),
        )

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            "UPDATE process_workspaces SET status = 'closed' WHERE id = %s",
            (ws_id,),
        )

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        with pytest.raises(psycopg.errors.RaiseException):
            cur.execute(
                "UPDATE process_workspaces SET status = 'sealed' WHERE id = %s",
                (ws_id,),
            )


@pytest.mark.db_integrity
def test_committee_session_sealed_to_draft_rejected(db_conn):
    """committee_sessions sealed -> draft doit lever une exception."""
    with db_conn.cursor() as cur:
        ws_id, tenant_id, _ = _setup_workspace(cur)
        session_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO committee_sessions
                (id, workspace_id, tenant_id)
            VALUES (%s, %s, %s)
            """,
            (session_id, ws_id, tenant_id),
        )
        cur.execute(
            "UPDATE committee_sessions SET session_status = 'sealed' WHERE id = %s",
            (session_id,),
        )

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        with pytest.raises(psycopg.errors.RaiseException):
            cur.execute(
                "UPDATE committee_sessions SET session_status = 'draft' WHERE id = %s",
                (session_id,),
            )


@pytest.mark.db_integrity
def test_committee_session_sealed_to_closed_ok(db_conn):
    """committee_sessions sealed -> closed doit réussir."""
    with db_conn.cursor() as cur:
        ws_id, tenant_id, _ = _setup_workspace(cur)
        session_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO committee_sessions
                (id, workspace_id, tenant_id)
            VALUES (%s, %s, %s)
            """,
            (session_id, ws_id, tenant_id),
        )
        cur.execute(
            "UPDATE committee_sessions SET session_status = 'sealed' WHERE id = %s",
            (session_id,),
        )

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            "UPDATE committee_sessions SET session_status = 'closed' WHERE id = %s",
            (session_id,),
        )
        cur.execute(
            "SELECT session_status FROM committee_sessions WHERE id = %s",
            (session_id,),
        )
        row = cur.fetchone()
        assert row["session_status"] == "closed"
