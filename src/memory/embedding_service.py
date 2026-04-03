"""Embedding service — wraps BGE-M3 (or stub for tests).

In production: uses FlagEmbedding BGE-M3 locally (0 API calls).
In tests/CI: uses a deterministic stub that returns fixed-dim vectors.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol, runtime_checkable

from src.memory.chunker_models import DocumentChunk
from src.memory.embedding_models import EmbeddingResult


class EmbeddingService:
    """Wraps an embedding backend (real BGE-M3 or stub)."""

    def __init__(self, backend: _EmbeddingBackend | None = None) -> None:
        self._backend = backend or _StubBackend()

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[EmbeddingResult]:
        results: list[EmbeddingResult] = []
        for chunk in chunks:
            dense, sparse = self._backend.encode(chunk.text)
            results.append(
                EmbeddingResult(
                    chunk_index=chunk.chunk_index,
                    dense=dense,
                    sparse=sparse,
                )
            )
        return results

    def embed_query(self, query: str) -> EmbeddingResult:
        dense, sparse = self._backend.encode(query)
        return EmbeddingResult(chunk_index=0, dense=dense, sparse=sparse)


@runtime_checkable
class _EmbeddingBackend(Protocol):
    def encode(self, text: str) -> tuple[list[float], dict[str, float]]: ...


class _StubBackend:
    """Deterministic stub — hash-based vectors for reproducible tests."""

    _DIM = 1024

    def encode(self, text: str) -> tuple[list[float], dict[str, float]]:
        h = hashlib.sha256(text.encode()).hexdigest()
        dense = [
            math.sin(int(h[i : i + 2], 16) * 0.01)
            for i in range(0, min(len(h), self._DIM * 2), 2)
        ]
        while len(dense) < self._DIM:
            dense.append(0.0)
        dense = dense[: self._DIM]
        norm = math.sqrt(sum(x * x for x in dense))
        if norm > 0:
            dense = [x / norm for x in dense]
        sparse: dict[str, float] = {}
        words = text.lower().split()[:20]
        for w in words:
            sparse[w] = 1.0
        return dense, sparse
