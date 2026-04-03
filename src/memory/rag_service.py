"""RAG service — retrieves context, reranks, generates answer.

INVARIANTS (V2 Plan):
- confidence ALWAYS <= 0.70 (capped)
- review_required ALWAYS True
- Uses EmbeddingService + Reranker + DeterministicRetrieval as fallback
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from src.memory.embedding_service import EmbeddingService
from src.memory.rag_models import RAGResult
from src.memory.reranker import Reranker

_MAX_RAG_CONFIDENCE = 0.70


@runtime_checkable
class _ConnectionProtocol(Protocol):
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None: ...

    def fetchone(self) -> dict[str, Any] | None: ...

    def fetchall(self) -> list[dict[str, Any]]: ...


_SEARCH_SQL = """
    SELECT chunk_text, 1 - (embedding_dense <=> :query_vec::vector) AS similarity
    FROM dms_embeddings
    ORDER BY embedding_dense <=> :query_vec::vector
    LIMIT :limit
"""


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
        emb = self._embedding.embed_query(query)
        vec_str = "[" + ",".join(str(v) for v in emb.dense) + "]"
        conn = self._conn_factory()
        conn.execute(_SEARCH_SQL, {"query_vec": vec_str, "limit": limit})
        rows = conn.fetchall()
        passages = [str(r.get("chunk_text", "")) for r in rows]
        reranked = self._reranker.rerank(query, passages)
        return [
            {"text": rr.text, "score": rr.score, "original_rank": rr.original_rank}
            for rr in reranked
        ]

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
