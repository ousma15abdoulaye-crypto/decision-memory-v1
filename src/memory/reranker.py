"""Cross-encoder reranker — stub for CI, real for production.

Production: uses bge-reranker-v2-m3 via FlagEmbedding.
Stub: score = 1.0 / (rank + 1) for deterministic ordering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RerankedResult:
    text: str
    original_rank: int
    score: float


@runtime_checkable
class _RerankerBackend(Protocol):
    def rerank(self, query: str, passages: list[str]) -> list[float]: ...


class _StubRerankerBackend:
    """Deterministic stub — score = 1/(rank+1)."""

    def rerank(self, query: str, passages: list[str]) -> list[float]:
        return [1.0 / (i + 1) for i in range(len(passages))]


class Reranker:
    """Reranks passages by cross-encoder score."""

    def __init__(self, backend: _RerankerBackend | None = None) -> None:
        self._backend = backend or _StubRerankerBackend()

    def rerank(
        self, query: str, passages: list[str], top_k: int = 5
    ) -> list[RerankedResult]:
        if not passages:
            return []
        scores = self._backend.rerank(query, passages)
        ranked = sorted(
            [
                RerankedResult(text=p, original_rank=i, score=s)
                for i, (p, s) in enumerate(zip(passages, scores))
            ],
            key=lambda r: r.score,
            reverse=True,
        )
        return ranked[:top_k]
