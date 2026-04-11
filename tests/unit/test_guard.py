"""M-CTO-V53-C — ``guard()`` JWT fallback : pas d'écriture sans membership DB."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from src.auth.guard import WRITE_PERMISSIONS, guard


def _user_buyer(uid: int = 7) -> dict:
    return {"id": uid, "role": "buyer", "tenant_id": str(uuid.uuid4())}


@pytest.mark.asyncio
async def test_jwt_fallback_denies_write_without_membership() -> None:
    """WRITE_PERMISSIONS exigent une ligne membership ; fallback JWT ne suffit pas."""
    from fastapi import HTTPException

    conn = AsyncMock()
    conn.fetch_one = AsyncMock(return_value=None)
    ws_id = uuid.uuid4()

    with patch("src.auth.guard.get_settings") as gs:
        gs.return_value.WORKSPACE_ACCESS_JWT_FALLBACK = True
        with pytest.raises(HTTPException) as ei:
            await guard(conn, _user_buyer(), ws_id, "evaluation.write")
        assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_jwt_fallback_allows_read_without_membership() -> None:
    """Lecture (hors WRITE_PERMISSIONS) peut passer par fallback pilote."""
    conn = AsyncMock()
    conn.fetch_one = AsyncMock(return_value=None)
    ws_id = uuid.uuid4()

    with patch("src.auth.guard.get_settings") as gs:
        gs.return_value.WORKSPACE_ACCESS_JWT_FALLBACK = True
        out = await guard(conn, _user_buyer(), ws_id, "evaluation.read")
    assert out["role"] == "supply_chain"


@pytest.mark.parametrize("permission", sorted(WRITE_PERMISSIONS))
@pytest.mark.asyncio
async def test_jwt_fallback_denies_all_write_permissions(permission: str) -> None:
    from fastapi import HTTPException

    conn = AsyncMock()
    conn.fetch_one = AsyncMock(return_value=None)
    ws_id = uuid.uuid4()

    with patch("src.auth.guard.get_settings") as gs:
        gs.return_value.WORKSPACE_ACCESS_JWT_FALLBACK = True
        with pytest.raises(HTTPException) as ei:
            await guard(conn, _user_buyer(uid=99), ws_id, permission)
        assert ei.value.status_code == 403
