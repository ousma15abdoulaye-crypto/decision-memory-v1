"""Tests — LangfuseIntegration (local DB recording, no Langfuse SDK)."""

from __future__ import annotations

from typing import Any

from src.memory.langfuse_integration import LangfuseIntegration, LLMTraceRecord


class MockConn:
    def __init__(self) -> None:
        self.last_sql: str = ""
        self.last_params: dict[str, Any] | None = None
        self._fetchone_result: dict[str, Any] | None = None

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        self.last_sql = sql
        self.last_params = params

    def fetchone(self) -> dict[str, Any] | None:
        return self._fetchone_result

    def fetchall(self) -> list[dict[str, Any]]:
        return []

    def set_fetchone(self, result: dict[str, Any] | None) -> None:
        self._fetchone_result = result


class TestRecordTrace:
    def test_inserts_and_returns_trace_id(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"trace_id": "abc-def"})
        svc = LangfuseIntegration(lambda: conn)
        record = LLMTraceRecord(
            operation="m12_classify",
            model_name="mistral-large",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            latency_ms=1200,
        )
        trace_id = svc.record_trace(record)
        assert trace_id == "abc-def"
        assert "INSERT INTO llm_traces" in conn.last_sql

    def test_returns_none_when_no_returning(self) -> None:
        conn = MockConn()
        conn.set_fetchone(None)
        svc = LangfuseIntegration(lambda: conn)
        record = LLMTraceRecord(operation="test", model_name="test-model")
        assert svc.record_trace(record) is None

    def test_params_complete(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"trace_id": "x"})
        svc = LangfuseIntegration(lambda: conn)
        record = LLMTraceRecord(
            operation="m13_regime",
            model_name="mistral-medium",
            provider="openrouter",
            cost_usd=0.001,
        )
        svc.record_trace(record)
        assert conn.last_params is not None
        assert conn.last_params["operation"] == "m13_regime"
        assert conn.last_params["provider"] == "openrouter"


class TestCountTraces:
    def test_count_all(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"c": 42})
        svc = LangfuseIntegration(lambda: conn)
        assert svc.count_traces() == 42

    def test_count_by_operation(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"c": 7})
        svc = LangfuseIntegration(lambda: conn)
        assert svc.count_traces(operation="m12_classify") == 7
        assert "operation" in conn.last_sql

    def test_count_returns_zero_on_none(self) -> None:
        conn = MockConn()
        conn.set_fetchone(None)
        svc = LangfuseIntegration(lambda: conn)
        assert svc.count_traces() == 0
