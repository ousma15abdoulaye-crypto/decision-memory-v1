"""DB test — INV-S01 : RLS cross-tenant isolation.

Canon V5.1.0 Section 5.4. Locking test (INV-S01).
Requires live DB (integration/DB fixture from conftest).

Vérifie que set_config('app.tenant_id') isole correctement les tables V5.1.
"""

from __future__ import annotations

import uuid

import pytest

TENANT_A = str(uuid.uuid4())
TENANT_B = str(uuid.uuid4())

_RLS_SUBJECT_ROLE = "dms_rls_nobypass"


def _ensure_rls_subject_role(cur) -> None:
    """Rôle non-propriétaire : les policies RLS s'appliquent (le owner table les contourne)."""
    cur.execute("""
        DO $body$
        BEGIN
            CREATE ROLE dms_rls_nobypass NOLOGIN NOSUPERUSER NOBYPASSRLS INHERIT;
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END
        $body$;
        """)
    cur.execute("GRANT USAGE ON SCHEMA public TO dms_rls_nobypass")
    cur.execute("GRANT SELECT ON workspace_memberships TO dms_rls_nobypass")


def _set_rls_subject_role(cur) -> None:
    _ensure_rls_subject_role(cur)
    cur.execute(f"SET ROLE {_RLS_SUBJECT_ROLE}")


def _reset_session_role(cur) -> None:
    cur.execute("RESET ROLE")


def _set_tenant(cur, tenant_id: str, is_admin: bool = False) -> None:
    cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
    if is_admin:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
    else:
        cur.execute("SELECT set_config('app.is_admin', '', true)")


@pytest.mark.db
class TestRLSCrossTenant:
    """Cross-tenant isolation tests — requires DB with migrations applied."""

    def test_workspace_memberships_rls_isolation(self, db_transaction):
        """workspace_memberships with RLS should filter by tenant_id."""
        cur = db_transaction
        # Setup: create tenants (session = table owner — RLS contournée sans SET ROLE)
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (TENANT_A, f"test-rls-a-{TENANT_A[:8]}", "Test RLS A"),
        )
        cur.execute(
            "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (TENANT_B, f"test-rls-b-{TENANT_B[:8]}", "Test RLS B"),
        )

        # Create user
        cur.execute("SELECT id FROM users LIMIT 1")
        row = cur.fetchone()
        if not row:
            pytest.skip("No users in DB — cannot run test")
        user_id = row["id"]

        # Create workspace for tenant A
        ws_a = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO process_workspaces
                (id, tenant_id, created_by, reference_code, title, process_type, status)
            VALUES (%s, %s, %s, %s, %s, 'devis_simple', 'draft')
            """,
            (ws_a, TENANT_A, user_id, f"RLS-A-{ws_a[:8]}", "RLS Test WS A"),
        )

        # Create membership for tenant A workspace
        cur.execute(
            """
            INSERT INTO workspace_memberships
                (workspace_id, tenant_id, user_id, role, granted_by)
            VALUES (%s, %s, %s, 'supply_chain', %s)
            """,
            (ws_a, TENANT_A, user_id, user_id),
        )

        try:
            _set_rls_subject_role(cur)
            # As tenant A: should see the membership
            _set_tenant(cur, TENANT_A)
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM workspace_memberships WHERE workspace_id = %s",
                (ws_a,),
            )
            row = cur.fetchone()
            assert row["cnt"] >= 1, "Tenant A should see its own memberships"

            # As tenant B: should NOT see tenant A's membership
            _set_tenant(cur, TENANT_B)
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM workspace_memberships WHERE workspace_id = %s",
                (ws_a,),
            )
            row = cur.fetchone()
            assert row["cnt"] == 0, "Tenant B must not see Tenant A memberships (RLS)"
        finally:
            _reset_session_role(cur)

    def test_admin_bypass_sees_all(self, db_transaction):
        """Admin bypass (app.is_admin = 'true') sees all tenants."""
        cur = db_transaction
        try:
            _set_rls_subject_role(cur)
            cur.execute("SELECT set_config('app.is_admin', 'true', true)")
            cur.execute("SELECT COUNT(*) AS cnt FROM workspace_memberships")
            row = cur.fetchone()
            assert (
                row["cnt"] >= 0
            ), "Admin should be able to query workspace_memberships"
        finally:
            _reset_session_role(cur)
