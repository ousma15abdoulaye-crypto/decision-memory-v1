"""Embedding service — wraps BGE-M3 (or stub for CI/tests).

Production: ``_BGEBackend`` using FlagEmbedding BAAI/bge-m3 (local, 0 API calls).
CI/tests: ``_StubBackend`` (hash-based, deterministic, no GPU/RAM requirements).

Backend selection:
    1. Explicit ``backend`` arg passed to ``EmbeddingService(backend=...)``
    2. ``FlagEmbedding`` importable + ``BGE_MODEL_PATH`` env set → ``_BGEBackend``
    3. Fallback → ``_StubBackend``

See ADR-H3-BGE-M3-001 for justification.
"""

from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol, runtime_checkable

from src.memory.chunker_models import DocumentChunk
from src.memory.embedding_models import EmbeddingResult

_BGE_AVAILABLE = False
try:
    from FlagEmbedding import (
        BGEM3FlagModel as _BGEM3FlagModel,  # type: ignore[import-not-found]
    )

    _BGE_AVAILABLE = True
except ImportError:
    _BGEM3FlagModel = None  # type: ignore[assignment,misc]


@runtime_checkable
class _EmbeddingBackend(Protocol):
    def encode(self, text: str) -> tuple[list[float], dict[str, float]]: ...


class _BGEBackend:
    """Production backend — BGE-M3 via FlagEmbedding (local, fp16).

    Loaded lazily on first call to reduce cold-start impact.
    """

    _DIM = 1024

    def __init__(self, model_name: str = "BAAI/bge-m3", use_fp16: bool = True) -> None:
        self._model_name = model_name
        self._use_fp16 = use_fp16
        self._model = None

    def _get_model(self):
        if self._model is None:
            if not _BGE_AVAILABLE:
                raise RuntimeError(
                    "FlagEmbedding not installed — cannot use _BGEBackend"
                )
            self._model = _BGEM3FlagModel(self._model_name, use_fp16=self._use_fp16)
        return self._model

    def encode(self, text: str) -> tuple[list[float], dict[str, float]]:
        model = self._get_model()
        output = model.encode(
            [text],
            batch_size=1,
            max_length=8192,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        # Dense: list of floats
        dense_raw = output["dense_vecs"][0]
        dense: list[float] = [float(v) for v in dense_raw]

        # Sparse: dict token_id → weight (convert to str keys for JSON compat)
        sparse_raw = output.get("lexical_weights", [{}])[0]
        sparse: dict[str, float] = {str(k): float(v) for k, v in sparse_raw.items()}

        return dense, sparse


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


def _build_default_backend() -> _EmbeddingBackend:
    """Select backend: BGE-M3 if available + configured, else stub."""
    if _BGE_AVAILABLE and os.environ.get("BGE_MODEL_PATH"):
        try:
            model_name = os.environ.get("BGE_MODEL_PATH", "BAAI/bge-m3")
            return _BGEBackend(model_name=model_name)
        except Exception:
            pass
    return _StubBackend()


class EmbeddingService:
    """Wraps an embedding backend (real BGE-M3 or stub)."""

    def __init__(self, backend: _EmbeddingBackend | None = None) -> None:
        self._backend = backend or _build_default_backend()

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
