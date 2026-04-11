"""RAG service — retrieves context, reranks, generates answer.

INVARIANTS (V2 Plan):
- confidence ALWAYS <= 0.70 (capped)
- review_required ALWAYS True
- find_similar_hybrid(): dense cosine + sparse BM25-style fusion (GAP-10)
- EmbeddingService + Reranker + DeterministicRetrieval as fallback
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from src.memory.embedding_service import EmbeddingService
from src.memory.rag_models import RAGResult
from src.memory.reranker import Reranker

_MAX_RAG_CONFIDENCE = 0.70
_DENSE_CANDIDATE_MULTIPLIER = 3  # fetch N*3 dense candidates for reranking with sparse


@runtime_checkable
class _ConnectionProtocol(Protocol):
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None: ...

    def fetchone(self) -> dict[str, Any] | None: ...

    def fetchall(self) -> list[dict[str, Any]]: ...


# Dense-only retrieval (first pass candidates)
_DENSE_SEARCH_SQL = """
    SELECT
        id::text             AS id,
        chunk_text,
        embedding_sparse,
        1 - (embedding_dense <=> :query_vec::vector) AS dense_similarity
    FROM dms_embeddings
    ORDER BY embedding_dense <=> :query_vec::vector
    LIMIT :limit
"""


def _row_as_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    return {str(k): row[k] for k in row.keys()}


def _sparse_dot_product(
    query_sparse: dict[str, float], doc_sparse: dict[str, float]
) -> float:
    """BM25-style dot product between query and document sparse vectors."""
    if not query_sparse or not doc_sparse:
        return 0.0
    score = 0.0
    for token, qw in query_sparse.items():
        dw = doc_sparse.get(token, 0.0)
        score += qw * dw
    return score


def _hybrid_score(
    dense_sim: float,
    sparse_sim: float,
    alpha: float = 0.7,
) -> float:
    """Weighted combination: alpha * dense + (1-alpha) * sparse."""
    return alpha * dense_sim + (1.0 - alpha) * sparse_sim


def _rerank_from_dense_rows(
    rows: list[dict[str, Any]],
    query: str,
    query_sparse: dict[str, float],
    limit: int,
    reranker: Reranker,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for r in rows:
        dense_sim = float(r.get("dense_similarity", 0.0) or 0.0)
        raw_sparse = r.get("embedding_sparse") or {}
        if isinstance(raw_sparse, str):
            try:
                raw_sparse = json.loads(raw_sparse)
            except Exception:
                raw_sparse = {}
        doc_sparse: dict[str, float] = {str(k): float(v) for k, v in raw_sparse.items()}
        sparse_sim = _sparse_dot_product(query_sparse, doc_sparse)
        sparse_sim_norm = min(sparse_sim / 5.0, 1.0) if sparse_sim > 0 else 0.0
        hybrid = _hybrid_score(dense_sim, sparse_sim_norm)
        candidates.append(
            {
                "id": str(r.get("id", "")),
                "text": str(r.get("chunk_text", "")),
                "dense_similarity": dense_sim,
                "sparse_similarity": sparse_sim_norm,
                "hybrid_score": hybrid,
            }
        )
    candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)
    top_candidates = candidates[:limit]
    passages = [c["text"] for c in top_candidates]
    reranked = reranker.rerank(query, passages, top_k=limit)
    return [
        {
            "text": rr.text,
            "score": rr.score,
            "original_rank": rr.original_rank,
            "hybrid_score": (
                top_candidates[rr.original_rank]["hybrid_score"]
                if rr.original_rank < len(top_candidates)
                else 0.0
            ),
        }
        for rr in reranked
    ]


async def find_similar_hybrid_async(
    db: Any,
    query: str,
    limit: int = 10,
    *,
    embedding_service: EmbeddingService | None = None,
    reranker: Reranker | None = None,
) -> list[dict[str, Any]]:
    """Même pipeline que ``RAGService.find_similar_hybrid`` via ``AsyncpgAdapter``.

    Utilise ``EmbeddingService`` (BGE-M3 ou stub) — pas les embeddings Mistral du routeur.
    """
    emb_svc = embedding_service or EmbeddingService()
    rr = reranker or Reranker()
    emb = emb_svc.embed_query(query)
    vec_str = "[" + ",".join(str(v) for v in emb.dense) + "]"
    rows_raw = await db.fetch_all(
        _DENSE_SEARCH_SQL,
        {"query_vec": vec_str, "limit": limit * _DENSE_CANDIDATE_MULTIPLIER},
    )
    rows = [_row_as_dict(r) for r in rows_raw]
    return _rerank_from_dense_rows(rows, query, emb.sparse, limit, rr)


class RAGService:
    """Retrieve-rerank-generate pipeline."""

    def __init__(
        self,
        conn_factory: Callable[[], _ConnectionProtocol],
        embedding_service: EmbeddingService | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self._conn_factory = conn_factory
        self._embedding = embedding_service or EmbeddingService()
        self._reranker = reranker or Reranker()

    def find_similar_hybrid(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Hybrid dense + sparse retrieval with cross-encoder reranking.

        1. Embed query (dense + sparse via BGE-M3 or stub).
        2. Fetch top N*3 candidates by dense similarity.
        3. Rescore each candidate by hybrid score (dense + sparse dot product).
        4. Cross-encoder rerank top-K for final ordering.
        """
        emb = self._embedding.embed_query(query)
        vec_str = "[" + ",".join(str(v) for v in emb.dense) + "]"
        query_sparse = emb.sparse

        conn = self._conn_factory()
        conn.execute(
            _DENSE_SEARCH_SQL,
            {"query_vec": vec_str, "limit": limit * _DENSE_CANDIDATE_MULTIPLIER},
        )
        rows = conn.fetchall()
        return _rerank_from_dense_rows(rows, query, query_sparse, limit, self._reranker)

    def answer_with_context(self, query: str, context_limit: int = 5) -> RAGResult:
        results = self.find_similar_hybrid(query, limit=context_limit * 2)
        sources = [r["text"][:200] for r in results[:context_limit]]
        raw_confidence = min(r["score"] for r in results[:1]) if results else 0.0
        confidence = min(raw_confidence, _MAX_RAG_CONFIDENCE)
        return RAGResult(
            answer=f"Based on {len(sources)} source(s): {query}",
            confidence=round(confidence, 2),
            review_required=True,
            sources=sources,
            reasoning=f"Retrieved {len(results)} passages, reranked top-{context_limit}",
        )
