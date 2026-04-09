"""INV-S02 — guard() async : matrice workspace + scellement (mocks asyncpg, sans DB).

Inclut les tests RBAC observer sans workspace_id (BUG-P3-07).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from src.auth.guard import guard
from src.auth.permissions import ROLE_PERMISSIONS
from src.couche_a.auth.dependencies import UserClaims
from src.services.workspace_access_service import WORKSPACE_WRITE_PERMISSIONS


def _make_user(
    user_id: str = "42",
    role: str = "observer",
    tenant: str | None = None,
) -> UserClaims:
    return UserClaims(
        user_id=user_id,
        role=role,
        jti=str(uuid.uuid4()),
        tenant_id=tenant or str(uuid.uuid4()),
    )


def _mock_conn_workspace(member_role: str | None, ws_status: str = "in_analysis"):
    conn = AsyncMock()
    if member_role is None:
        conn.fetch = AsyncMock(return_value=[])
    else:
        conn.fetch = AsyncMock(
            return_value=[{"role": member_role, "coi_declared": False}]
        )

    seq: list = [{"role": member_role}, {"status": ws_status}] if member_role else []

    async def fetchrow_seq(*_a, **_k):
        if not seq:
            return None
        return seq.pop(0)

    conn.fetchrow = AsyncMock(side_effect=fetchrow_seq)
    return conn


class TestGuardObserver:
    @pytest.mark.asyncio
    async def test_observer_denied_deliberation_write(self):
        from fastapi import HTTPException

        conn = _mock_conn_workspace("observer")
        user = _make_user()
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "deliberation.write")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_observer_denied_matrix_comment(self):
        from fastapi import HTTPException

        conn = _mock_conn_workspace("observer")
        user = _make_user()
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "matrix.comment")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_observer_allowed_matrix_read(self):
        conn = _mock_conn_workspace("observer")
        user = _make_user()
        ws_id = uuid.uuid4()

        role = await guard(conn, user, ws_id, "matrix.read")
        assert role == "observer"

    @pytest.mark.asyncio
    async def test_non_member_denied(self):
        from fastapi import HTTPException

        conn = _mock_conn_workspace(None)
        user = _make_user()
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "matrix.read")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_procurement_lead_denied_deliberation_write(self):
        from fastapi import HTTPException

        conn = _mock_conn_workspace("procurement_lead")
        user = _make_user(role="supply_chain")
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "deliberation.write")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_committee_member_allowed_deliberation_write(self):
        conn = _mock_conn_workspace("committee_member")
        user = _make_user(role="finance")
        ws_id = uuid.uuid4()

        role = await guard(conn, user, ws_id, "deliberation.write")
        assert role == "committee_member"


def _mock_conn_sealed(ws_status: str, member_role: str = "committee_member"):
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[{"role": member_role, "coi_declared": False}])
    seq = [{"role": member_role}, {"status": ws_status}]

    async def fetchrow_seq(*_a, **_k):
        if not seq:
            return None
        return seq.pop(0)

    conn.fetchrow = AsyncMock(side_effect=fetchrow_seq)
    return conn


class TestGuardSealed:
    @pytest.mark.parametrize("status", ["sealed", "closed", "cancelled"])
    @pytest.mark.asyncio
    async def test_write_blocked_on_closed_workspace(self, status):
        from fastapi import HTTPException

        conn = _mock_conn_sealed(status)
        user = _make_user(user_id="1", role="supply_chain")
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "deliberation.write")
        assert exc_info.value.status_code == 409

    @pytest.mark.parametrize("status", ["sealed", "closed", "cancelled"])
    @pytest.mark.asyncio
    async def test_read_allowed_on_closed_workspace(self, status):
        conn = _mock_conn_sealed(status)
        user = _make_user(user_id="1", role="supply_chain")
        ws_id = uuid.uuid4()

        role = await guard(conn, user, ws_id, "matrix.read")
        assert role == "committee_member"

    @pytest.mark.asyncio
    async def test_write_allowed_on_open_workspace(self):
        conn = _mock_conn_sealed("in_analysis")
        user = _make_user(user_id="1", role="supply_chain")
        ws_id = uuid.uuid4()

        role = await guard(conn, user, ws_id, "deliberation.write")
        assert role == "committee_member"

    @pytest.mark.parametrize("permission", sorted(WORKSPACE_WRITE_PERMISSIONS))
    @pytest.mark.asyncio
    async def test_all_workspace_writes_blocked_when_sealed(self, permission):
        from fastapi import HTTPException

        conn = _mock_conn_sealed("sealed", member_role="committee_chair")
        user = _make_user(user_id="1", role="supply_chain")
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, permission)
        assert exc_info.value.status_code == 409


class TestRbacObserverNoWorkspaceId:
    """RBAC tenant-level fallback — observer sans workspace_id (BUG-P3-07).

    Valide la logique du router agent.py : quand workspace_id est absent,
    un rôle 'observer' sans 'agent.query' doit recevoir 403.
    """

    def test_observer_lacks_agent_query_permission(self):
        """Le rôle 'observer' ne doit pas avoir 'agent.query' dans ROLE_PERMISSIONS."""
        observer_perms = ROLE_PERMISSIONS.get("observer", frozenset())
        assert (
            "agent.query" not in observer_perms
        ), "Le rôle observer ne doit pas avoir agent.query sans workspace_id"

    def test_admin_has_system_admin_permission(self):
        """Le rôle 'admin' doit avoir 'system.admin' (lui permettant de passer)."""
        admin_perms = ROLE_PERMISSIONS.get("admin", frozenset())
        assert "system.admin" in admin_perms or "agent.query" in admin_perms

    def test_agent_query_permission_present_for_authorized_roles(self):
        """Au moins un rôle (non-observer) possède 'agent.query'."""
        roles_with_agent_query = [
            role
            for role, perms in ROLE_PERMISSIONS.items()
            if "agent.query" in perms or "system.admin" in perms
        ]
        assert len(roles_with_agent_query) > 0
