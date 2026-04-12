"""Tests batch embeddings (warm centroïdes, réduction appels Mistral)."""

from __future__ import annotations

import asyncio

import numpy as np

from src.agent.embedding_client import (
    get_embeddings_batch,
    reset_embedding_client_state,
)


def _run(coro):
    return asyncio.run(coro)


class TestGetEmbeddingsBatch:
    def setup_method(self):
        reset_embedding_client_state()

    def test_empty_returns_empty(self):
        assert _run(get_embeddings_batch([])) == []

    def test_length_matches_inputs(self):
        texts = ["a", "b", "c"]
        out = _run(get_embeddings_batch(texts))
        assert len(out) == 3
        for arr in out:
            assert isinstance(arr, np.ndarray)
            assert arr.shape == (1024,)
