"""Tests — garde-fou schéma 096 avant handler RAG."""

from __future__ import annotations

from typing import Any

import pytest

from src.memory.rag_service import dms_embeddings_tenant_isolation_ready


class _MockDbFetchOne:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row

    async def fetch_one(self, sql: str, params: dict[str, Any]) -> Any:
        _ = sql, params
        return self._row


@pytest.mark.asyncio
async def test_dms_embeddings_tenant_isolation_ready_true() -> None:
    db = _MockDbFetchOne({"ok": 1})
    assert await dms_embeddings_tenant_isolation_ready(db) is True


@pytest.mark.asyncio
async def test_dms_embeddings_tenant_isolation_ready_false() -> None:
    db = _MockDbFetchOne(None)
    assert await dms_embeddings_tenant_isolation_ready(db) is False
