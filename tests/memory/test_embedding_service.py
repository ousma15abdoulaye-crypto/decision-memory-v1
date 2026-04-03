"""Tests — EmbeddingService (stub backend)."""

from __future__ import annotations

from src.memory.chunker_models import DocumentChunk
from src.memory.embedding_models import EmbeddingResult
from src.memory.embedding_service import EmbeddingService


def _chunk(text: str = "test chunk", idx: int = 0) -> DocumentChunk:
    return DocumentChunk(
        chunk_index=idx,
        text=text,
        start_char=0,
        end_char=len(text),
    )


class TestEmbedChunks:
    def test_returns_results(self) -> None:
        svc = EmbeddingService()
        results = svc.embed_chunks([_chunk()])
        assert len(results) == 1
        assert isinstance(results[0], EmbeddingResult)

    def test_dense_dimension_1024(self) -> None:
        svc = EmbeddingService()
        result = svc.embed_chunks([_chunk()])[0]
        assert len(result.dense) == 1024

    def test_sparse_populated(self) -> None:
        svc = EmbeddingService()
        result = svc.embed_chunks([_chunk("hello world")])[0]
        assert "hello" in result.sparse

    def test_multiple_chunks(self) -> None:
        svc = EmbeddingService()
        chunks = [_chunk("A", 0), _chunk("B", 1)]
        results = svc.embed_chunks(chunks)
        assert len(results) == 2
        assert results[0].chunk_index == 0
        assert results[1].chunk_index == 1

    def test_deterministic(self) -> None:
        svc = EmbeddingService()
        r1 = svc.embed_chunks([_chunk("same")])[0].dense
        r2 = svc.embed_chunks([_chunk("same")])[0].dense
        assert r1 == r2


class TestEmbedQuery:
    def test_returns_result(self) -> None:
        svc = EmbeddingService()
        result = svc.embed_query("test query")
        assert isinstance(result, EmbeddingResult)
        assert len(result.dense) == 1024

    def test_normalized(self) -> None:
        import math

        svc = EmbeddingService()
        result = svc.embed_query("normalization test")
        norm = math.sqrt(sum(x * x for x in result.dense))
        assert abs(norm - 1.0) < 0.01


class TestEmbeddingResultModel:
    def test_extra_forbid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="extra"):
            EmbeddingResult(chunk_index=0, dense=[0.0], rogue="x")
