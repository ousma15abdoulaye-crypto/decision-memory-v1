"""Integration test — INV-S02 : guard() bloque toute écriture sur workspace scellé.

Canon V5.1.0 Locking test 6.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.auth.guard import guard
from src.couche_a.auth.dependencies import UserClaims


def _make_user(user_id: str = "1") -> UserClaims:
    return UserClaims(
        user_id=user_id,
        role="supply_chain",
        jti=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
    )


def _mock_conn_sealed(ws_status: str):
    conn = AsyncMock()
    member_record = MagicMock()
    member_record.__getitem__ = lambda self, key: (
        "supply_chain" if key == "role" else ws_status
    )
    ws_record = MagicMock()
    ws_record.__getitem__ = lambda self, key: ws_status

    async def fetchrow_side_effect(query, *args):
        if "workspace_memberships" in query:
            return member_record
        return ws_record

    conn.fetchrow.side_effect = fetchrow_side_effect
    return conn


class TestGuardSealed:
    @pytest.mark.parametrize("status", ["sealed", "closed", "cancelled"])
    @pytest.mark.asyncio
    async def test_write_blocked_on_closed_workspace(self, status):
        from fastapi import HTTPException

        conn = _mock_conn_sealed(status)
        user = _make_user()
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "evaluation.write")
        assert exc_info.value.status_code == 409

    @pytest.mark.parametrize("status", ["sealed", "closed", "cancelled"])
    @pytest.mark.asyncio
    async def test_read_allowed_on_closed_workspace(self, status):
        conn = _mock_conn_sealed(status)
        user = _make_user()
        ws_id = uuid.uuid4()

        role = await guard(conn, user, ws_id, "evaluation.read")
        assert role == "supply_chain"

    @pytest.mark.asyncio
    async def test_write_allowed_on_open_workspace(self):
        conn = _mock_conn_sealed("open")
        user = _make_user()
        ws_id = uuid.uuid4()

        role = await guard(conn, user, ws_id, "evaluation.write")
        assert role == "supply_chain"

    @pytest.mark.parametrize(
        "permission",
        [
            "workspace.manage",
            "documents.upload",
            "documents.delete",
            "evaluation.write",
            "committee.comment",
            "committee.seal",
        ],
    )
    @pytest.mark.asyncio
    async def test_all_write_permissions_blocked_when_sealed(self, permission):
        from fastapi import HTTPException

        conn = _mock_conn_sealed("sealed")
        user = _make_user()
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, permission)
        assert exc_info.value.status_code == 409
