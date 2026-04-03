"""Langfuse integration — trace LLM calls with local DB backup.

Uses Langfuse SDK when available AND config/langfuse/langfuse_config.yaml
has ``langfuse.enabled: true``.  Falls back to local-only recording.
Every trace is ALSO written to llm_traces table for offline audit.

GAP-20 fix: reads langfuse_config.yaml in __init__ — if enabled=false,
_langfuse_client is forced to None regardless of SDK availability.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

_CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "config" / "langfuse" / "langfuse_config.yaml"
)


def _read_langfuse_enabled() -> bool:
    """Return True only if config/langfuse/langfuse_config.yaml has langfuse.enabled: true."""
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))
        return bool((data or {}).get("langfuse", {}).get("enabled", False))
    except Exception as exc:
        logger.warning(
            "LangfuseIntegration: could not read langfuse_config.yaml: %s", exc
        )
        return False


@runtime_checkable
class _ConnectionProtocol(Protocol):
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None: ...

    def fetchone(self) -> dict[str, Any] | None: ...

    def fetchall(self) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class LLMTraceRecord:
    operation: str
    model_name: str
    provider: str = "openrouter"
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    status: str = "success"
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


_INSERT_TRACE_SQL = """
    INSERT INTO llm_traces (
        operation, model_name, provider,
        input_tokens, output_tokens, total_tokens,
        latency_ms, cost_usd, status, error_message, metadata
    ) VALUES (
        :operation, :model_name, :provider,
        :input_tokens, :output_tokens, :total_tokens,
        :latency_ms, :cost_usd, :status, :error_message,
        CAST(:metadata AS jsonb)
    )
    RETURNING trace_id
"""


class LangfuseIntegration:
    """Records LLM traces to local DB (+ Langfuse when available)."""

    def __init__(self, conn_factory: Callable[[], _ConnectionProtocol]) -> None:
        self._conn_factory = conn_factory
        self._langfuse_client: Any = None
        if _read_langfuse_enabled():
            try:
                from langfuse import Langfuse

                self._langfuse_client = Langfuse()
                logger.info("LangfuseIntegration: Langfuse client initialized.")
            except (ImportError, Exception) as exc:
                logger.warning("LangfuseIntegration: Langfuse SDK unavailable: %s", exc)
        else:
            logger.debug(
                "LangfuseIntegration: Langfuse disabled (config: enabled=false)."
            )

    def record_trace(self, record: LLMTraceRecord) -> str | None:
        import json as _json

        conn = self._conn_factory()
        params = {
            "operation": record.operation,
            "model_name": record.model_name,
            "provider": record.provider,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "total_tokens": record.total_tokens,
            "latency_ms": record.latency_ms,
            "cost_usd": record.cost_usd,
            "status": record.status,
            "error_message": record.error_message,
            "metadata": _json.dumps(record.metadata, ensure_ascii=False),
        }
        conn.execute(_INSERT_TRACE_SQL, params)
        row = conn.fetchone()
        trace_id = str(row["trace_id"]) if row and "trace_id" in row else None
        if self._langfuse_client and trace_id:
            try:
                self._langfuse_client.trace(
                    name=record.operation,
                    metadata={"trace_id": trace_id, **record.metadata},
                )
            except Exception:
                pass
        return trace_id

    def count_traces(self, operation: str | None = None) -> int:
        conn = self._conn_factory()
        if operation:
            conn.execute(
                "SELECT COUNT(*) AS c FROM llm_traces WHERE operation = :op",
                {"op": operation},
            )
        else:
            conn.execute("SELECT COUNT(*) AS c FROM llm_traces", None)
        row = conn.fetchone()
        return int(row["c"]) if row else 0
