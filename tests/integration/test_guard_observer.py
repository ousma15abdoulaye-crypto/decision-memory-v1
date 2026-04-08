"""Integration test — INV-S02 : guard() bloque l'observer pour les writes.

Canon V5.1.0 Locking test 5.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.auth.guard import guard
from src.couche_a.auth.dependencies import UserClaims


def _make_user(user_id: str = "42", role: str = "observer") -> UserClaims:
    return UserClaims(
        user_id=user_id,
        role=role,
        jti=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
    )


def _mock_conn(member_role: str | None, ws_status: str = "open"):
    conn = AsyncMock()
    if member_role is None:
        conn.fetchrow.return_value = None
    else:
        member_record = MagicMock()
        member_record.__getitem__ = lambda self, key: (
            member_role if key == "role" else ws_status
        )
        ws_record = MagicMock()
        ws_record.__getitem__ = lambda self, key: ws_status

        async def fetchrow_side_effect(query, *args):
            if "workspace_memberships" in query:
                return member_record
            return ws_record

        conn.fetchrow.side_effect = fetchrow_side_effect
    return conn


class TestGuardObserver:
    @pytest.mark.asyncio
    async def test_observer_denied_evaluation_write(self):
        from fastapi import HTTPException

        conn = _mock_conn("observer")
        user = _make_user()
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "evaluation.write")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_observer_denied_committee_comment(self):
        from fastapi import HTTPException

        conn = _mock_conn("observer")
        user = _make_user()
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "committee.comment")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_observer_allowed_workspace_read(self):
        conn = _mock_conn("observer")
        user = _make_user()
        ws_id = uuid.uuid4()

        role = await guard(conn, user, ws_id, "workspace.read")
        assert role == "observer"

    @pytest.mark.asyncio
    async def test_non_member_denied(self):
        from fastapi import HTTPException

        conn = _mock_conn(None)
        user = _make_user()
        ws_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await guard(conn, user, ws_id, "workspace.read")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_supply_chain_allowed_evaluation_write(self):
        conn = _mock_conn("supply_chain")
        user = _make_user(role="supply_chain")
        ws_id = uuid.uuid4()

        role = await guard(conn, user, ws_id, "evaluation.write")
        assert role == "supply_chain"
