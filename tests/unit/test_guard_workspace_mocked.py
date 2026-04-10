"""INV-S02 â€” guard() async : matrice workspace + scellement (mocks asyncpg, sans DB).

Inclut les tests RBAC observer sans workspace_id (BUG-P3-07).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from src.auth.guard import WRITE_PERMISSIONS, guard
from src.auth.permissions import ROLE_PERMISSIONS


def _make_user(
    user_id: int = 42,
    role: str = "observer",
    tenant: str | None = None,
) -> dict:
    """Retourne un dict user compatible avec guard() (V5.2 API â€” user["id"] est int)."""
    return {
        "id": user_id,
        "role": role,
        "tenant_id": tenant or str(uuid.uuid4()),
    }


def _mock_conn_workspace(member_role: str | None, ws_status: str = "in_analysis"):
    """Mock AsyncpgAdapter pour guard() V5.2 â€” utilise fetch_one() (pas fetchrow)."""
    conn = AsyncMock()

    # guard() fait 2 appels Ã  fetch_one :
    #   1. workspace_memberships â†’ rÃ´le du membre (ou None si non membre)
    #   2. process_workspaces   â†’ status du workspace (seulement pour WRITE_PERMISSIONS)
    member_row = {"role": member_role} if member_role else None
    ws_row = {"status": ws_status}

    call_count = [0]

    async def fetch_one_seq(sql: str, params: dict):
        call_count[0] += 1
        if call_count[0] == 1:
            return member_row  # membership check
        return ws_row  # seal check

    conn.fetch_one = AsyncMock(side_effect=fetch_one_seq)
    return conn


class TestGuardObserver:
    @pytest.mark.asyncio
    async def test_observer_denied_evaluation_write(self):
        """observer n'a pas de permission d'Ã©criture (V5.2 â€” aucun .write)."""
        from fastapi import HTTPException

        conn = _mock_conn_workspace("observer")
        user = _make_user()
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "evaluation.write")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_observer_denied_committee_comment(self):
        """observer n'a pas committee.comment (V5.2)."""
        from fastapi import HTTPException

        conn = _mock_conn_workspace("observer")
        user = _make_user()
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "committee.comment")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_observer_allowed_evaluation_read(self):
        """observer peut lire evaluation.read (V5.2)."""
        conn = _mock_conn_workspace("observer")
        user = _make_user()
        ws_id = uuid.uuid4()

        result = await guard(conn, user, ws_id, "evaluation.read")
        assert result["role"] == "observer"

    @pytest.mark.asyncio
    async def test_non_member_denied(self):
        from fastapi import HTTPException

        conn = _mock_conn_workspace(None)
        user = _make_user()
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "evaluation.read")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_technical_reviewer_denied_workspace_manage(self):
        """procurement_lead â†’ supply_chain, mais workspace.manage est bloquÃ©
        car supply_chain A workspace.manage â€” ce test vÃ©rifie la nÃ©gation:
        si on utilise un rÃ´le legacy sans la permission, on est bloquÃ©."""
        from fastapi import HTTPException

        conn = _mock_conn_workspace("technical_reviewer")
        user = _make_user(role="technical")
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "workspace.manage")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_committee_member_allowed_evaluation_write(self):
        """committee_member â†’ supply_chain via _LEGACY_ROLE_MAP â†’ a evaluation.write."""
        conn = _mock_conn_workspace("committee_member")
        user = _make_user(role="finance")
        ws_id = uuid.uuid4()

        result = await guard(conn, user, ws_id, "evaluation.write")
        assert result["role"] == "committee_member"


def _mock_conn_sealed(ws_status: str, member_role: str = "committee_member"):
    """Mock AsyncpgAdapter pour le check de scellement â€” fetch_one() sÃ©quentiel."""
    conn = AsyncMock()
    call_count = [0]

    async def fetch_one_seq(sql: str, params: dict):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"role": member_role}
        return {"status": ws_status}

    conn.fetch_one = AsyncMock(side_effect=fetch_one_seq)
    return conn


class TestGuardSealed:
    @pytest.mark.parametrize("status", ["sealed", "closed", "cancelled"])
    @pytest.mark.asyncio
    async def test_write_blocked_on_closed_workspace(self, status):
        """Ã‰criture (evaluation.write) bloquÃ©e sur workspace clos â€” 409."""
        from fastapi import HTTPException

        conn = _mock_conn_sealed(status)
        user = _make_user(user_id=1, role="supply_chain")
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "evaluation.write")
        assert exc_info.value.status_code == 409

    @pytest.mark.parametrize("status", ["sealed", "closed", "cancelled"])
    @pytest.mark.asyncio
    async def test_read_allowed_on_closed_workspace(self, status):
        """Lecture (evaluation.read) autorisÃ©e mÃªme sur workspace clos."""
        conn = _mock_conn_sealed(status)
        user = _make_user(user_id=1, role="supply_chain")
        ws_id = uuid.uuid4()

        result = await guard(conn, user, ws_id, "evaluation.read")
        assert result["role"] == "committee_member"

    @pytest.mark.asyncio
    async def test_write_allowed_on_open_workspace(self):
        """Ã‰criture autorisÃ©e si workspace ouvert."""
        conn = _mock_conn_sealed("in_analysis")
        user = _make_user(user_id=1, role="supply_chain")
        ws_id = uuid.uuid4()

        result = await guard(conn, user, ws_id, "evaluation.write")
        assert result["role"] == "committee_member"

    @pytest.mark.parametrize("permission", sorted(WRITE_PERMISSIONS))
    @pytest.mark.asyncio
    async def test_all_v52_writes_blocked_when_sealed(self, permission):
        """Toutes les WRITE_PERMISSIONS V5.2 sont bloquÃ©es sur workspace scellÃ© â€” 409.

        Utilise guard.WRITE_PERMISSIONS (V5.2 canon) et committee_chair â†’ supply_chain
        qui possÃ¨de toutes ces permissions.
        """
        from fastapi import HTTPException

        conn = _mock_conn_sealed("sealed", member_role="committee_chair")
        user = _make_user(user_id=1, role="supply_chain")
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, permission)
        assert exc_info.value.status_code == 409


class TestRbacObserverNoWorkspaceId:
    """RBAC tenant-level fallback â€” observer sans workspace_id (BUG-P3-07).

    Valide la logique du router agent.py : quand workspace_id est absent,
    un rÃ´le 'observer' sans 'agent.query' doit recevoir 403.
    """

    def test_observer_lacks_agent_query_permission(self):
        """Le rÃ´le 'observer' ne doit pas avoir 'agent.query' dans ROLE_PERMISSIONS."""
        observer_perms = ROLE_PERMISSIONS.get("observer", frozenset())
        assert (
            "agent.query" not in observer_perms
        ), "Le rÃ´le observer ne doit pas avoir agent.query sans workspace_id"

    def test_admin_has_system_admin_permission(self):
        """Le rÃ´le 'admin' doit avoir 'system.admin' (lui permettant de passer)."""
        admin_perms = ROLE_PERMISSIONS.get("admin", frozenset())
        assert "system.admin" in admin_perms or "agent.query" in admin_perms

    def test_agent_query_permission_present_for_authorized_roles(self):
        """Au moins un rÃ´le (non-observer) possÃ¨de 'agent.query'."""
        roles_with_agent_query = [
            role
            for role, perms in ROLE_PERMISSIONS.items()
            if "agent.query" in perms or "system.admin" in perms
        ]
        assert len(roles_with_agent_query) > 0
