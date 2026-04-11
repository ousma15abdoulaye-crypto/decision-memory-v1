"""Tests — find_similar_hybrid_async (AsyncpgAdapter-compatible db)."""

from __future__ import annotations

from typing import Any

import pytest

from src.memory.rag_service import find_similar_hybrid_async


class _MockAsyncDb:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    async def fetch_all(self, sql: str, params: dict[str, Any]) -> list[Any]:
        _ = sql, params
        return list(self._rows)


@pytest.mark.asyncio
async def test_find_similar_hybrid_async_returns_texts() -> None:
    db = _MockAsyncDb(
        [
            {
                "id": "1",
                "chunk_text": "passage about RCCM and delays",
                "embedding_sparse": {},
                "dense_similarity": 0.92,
            }
        ]
    )
    out = await find_similar_hybrid_async(db, "RCCM requirements", limit=3)
    assert len(out) >= 1
    assert "text" in out[0]
    assert out[0]["text"]
    assert "id" in out[0] and out[0]["id"] == "1"
