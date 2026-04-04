"""Tests DB integrity — RLS isolation process_workspaces (REGLE-W01, INV-W05).

Vérifie :
- SELECT process_workspaces sans SET LOCAL -> 0 lignes (RLS)
- SELECT avec SET LOCAL tenant_a -> lignes tenant_a seulement
- SELECT avec app.is_admin = 'true' -> toutes les lignes

Pré-condition : migrations 068-069 appliquées. dm_app role disponible.
"""

from __future__ import annotations

import uuid

import pytest


def _make_tenant_and_workspace(cur, code: str) -> tuple[str, str]:
    cur.execute("SELECT set_config('app.is_admin', 'true', false)")
    cur.execute("SELECT id FROM tenants WHERE code = %s LIMIT 1", (code,))
    row = cur.fetchone()
    if row:
        tenant_id = str(row["id"])
    else:
        tenant_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s)",
            (tenant_id, code, f"Tenant {code}"),
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
        (ws_id, tenant_id, user_id, f"RLS-{ws_id[:8]}", "RLS Test", "devis_simple"),
    )
    return tenant_id, ws_id


@pytest.mark.db_integrity
def test_rls_no_local_set_returns_empty(db_conn):
    """Sans tenant_id en session, process_workspaces doit retourner 0 lignes."""
    with db_conn.cursor() as cur:
        _make_tenant_and_workspace(cur, "sci_mali")

    with db_conn.cursor() as cur:
        cur.execute("RESET app.is_admin")
        cur.execute("RESET app.tenant_id")
        cur.execute("SELECT count(*) AS n FROM process_workspaces")
        count = cur.fetchone()["n"]
        assert (
            count == 0
        ), f"RLS devrait masquer toutes les lignes sans tenant_id, got {count}"


@pytest.mark.db_integrity
def test_rls_tenant_isolation(db_conn):
    """Avec app.tenant_id = tenant_a, seules les lignes tenant_a sont visibles."""
    with db_conn.cursor() as cur:
        tenant_a_id, ws_a = _make_tenant_and_workspace(cur, "test_rls_tenant_a")
        _, _ws_b = _make_tenant_and_workspace(cur, "test_rls_tenant_b")

    with db_conn.cursor() as cur:
        cur.execute("RESET app.is_admin")
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (tenant_a_id,))
        cur.execute("SELECT id FROM process_workspaces WHERE id = %s", (ws_a,))
        assert cur.fetchone() is not None, "Workspace tenant_a devrait être visible"

        cur.execute("SELECT id FROM process_workspaces WHERE id = %s", (_ws_b,))
        assert cur.fetchone() is None, "Workspace tenant_b ne devrait pas être visible"

    with db_conn.cursor() as cur:
        cur.execute("RESET app.tenant_id")


@pytest.mark.db_integrity
def test_rls_admin_sees_all(db_conn):
    """Avec app.is_admin = 'true', toutes les lignes sont visibles."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        _make_tenant_and_workspace(cur, "test_rls_admin_a")
        _make_tenant_and_workspace(cur, "test_rls_admin_b")

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', false)")
        cur.execute("SELECT count(*) AS n FROM process_workspaces")
        count = cur.fetchone()["n"]
        assert count >= 2, "Admin devrait voir au moins 2 workspaces"

    with db_conn.cursor() as cur:
        cur.execute("RESET app.is_admin")
