"""Cross-encoder reranker — stub for CI, real BGE-Reranker for production.

Production: ``_BGERerankerBackend`` using BAAI/bge-reranker-v2-m3 (local, no API).
CI/tests: ``_StubRerankerBackend`` (rank-based, deterministic).

Backend selection:
    1. Explicit ``backend`` arg passed to ``Reranker(backend=...)``
    2. ``FlagEmbedding`` importable + ``BGE_RERANKER_MODEL`` env set → ``_BGERerankerBackend``
    3. Fallback → ``_StubRerankerBackend``

See ADR-H3-BGE-M3-001.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

_BGE_AVAILABLE = False
try:
    from FlagEmbedding import (
        FlagReranker as _FlagReranker,  # type: ignore[import-not-found]
    )

    _BGE_AVAILABLE = True
except ImportError:
    _FlagReranker = None  # type: ignore[assignment,misc]


@dataclass(frozen=True)
class RerankedResult:
    text: str
    original_rank: int
    score: float


@runtime_checkable
class _RerankerBackend(Protocol):
    def rerank(self, query: str, passages: list[str]) -> list[float]: ...


class _BGERerankerBackend:
    """Production reranker — BGE-reranker-v2-m3 via FlagEmbedding (local)."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        use_fp16: bool = True,
    ) -> None:
        self._model_name = model_name
        self._use_fp16 = use_fp16
        self._model = None

    def _get_model(self):
        if self._model is None:
            if not _BGE_AVAILABLE:
                raise RuntimeError(
                    "FlagEmbedding not installed — cannot use _BGERerankerBackend"
                )
            self._model = _FlagReranker(self._model_name, use_fp16=self._use_fp16)
        return self._model

    def rerank(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        model = self._get_model()
        pairs = [[query, p] for p in passages]
        scores = model.compute_score(pairs, normalize=True)
        return [float(s) for s in scores]


class _StubRerankerBackend:
    """Deterministic stub — score = 1/(rank+1)."""

    def rerank(self, query: str, passages: list[str]) -> list[float]:
        return [1.0 / (i + 1) for i in range(len(passages))]


def _build_default_reranker_backend() -> _RerankerBackend:
    """Select backend: BGE if available + configured, else stub."""
    if _BGE_AVAILABLE and os.environ.get("BGE_RERANKER_MODEL"):
        try:
            model_name = os.environ.get("BGE_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
            return _BGERerankerBackend(model_name=model_name)
        except Exception:
            pass
    return _StubRerankerBackend()


class Reranker:
    """Reranks passages by cross-encoder score."""

    def __init__(self, backend: _RerankerBackend | None = None) -> None:
        self._backend = backend or _build_default_reranker_backend()

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
