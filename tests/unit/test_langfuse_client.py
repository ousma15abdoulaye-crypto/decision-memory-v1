"""Tests unitaires — INV-A01 : Langfuse client (mode no-op).

Canon V5.1.0 Section 9.1. Locking test 13 (INV-A01).

Vérifie que le client se construit en mode no-op quand les clés
Langfuse sont absentes, et que le pattern de traçage fonctionne.
"""

from __future__ import annotations

import os
from unittest.mock import patch


class TestLangfuseClientNoOp:
    def setup_method(self):
        import src.agent.langfuse_client as lc

        lc._langfuse = None

    def teardown_method(self):
        import src.agent.langfuse_client as lc

        lc._langfuse = None

    def test_get_langfuse_without_keys_returns_noop(self):
        import src.agent.langfuse_client as lc

        with patch.dict(
            os.environ,
            {"LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": ""},
            clear=False,
        ):
            client = lc.get_langfuse()
        assert client is not None

    def test_noop_trace_has_span(self):
        from src.agent.langfuse_client import _NullLangfuse

        client = _NullLangfuse()
        trace = client.trace(name="test", metadata={"doc": "abc"})
        span = trace.span(name="extraction")
        span.end(output={"fields": 5})

    def test_noop_trace_id_is_none(self):
        from src.agent.langfuse_client import _NullTrace

        trace = _NullTrace()
        assert trace.id is None

    def test_flush_without_client(self):
        import src.agent.langfuse_client as lc

        lc.flush_langfuse()

    def test_flush_noop_client(self):
        import src.agent.langfuse_client as lc
        from src.agent.langfuse_client import _NullLangfuse

        lc._langfuse = _NullLangfuse()
        lc.flush_langfuse()

    def test_singleton_returns_same_instance(self):
        import src.agent.langfuse_client as lc

        with patch.dict(
            os.environ, {"LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": ""}
        ):
            c1 = lc.get_langfuse()
            c2 = lc.get_langfuse()
        assert c1 is c2

    def test_null_span_update_noop(self):
        from src.agent.langfuse_client import _NullTrace

        trace = _NullTrace()
        trace.update(output="done", usage={"total_tokens": 100})


class TestExtractionTracingPattern:
    """Vérifie que le pattern d'extraction Langfuse (Canon Section 9.4) fonctionne."""

    def test_extraction_trace_pattern(self):
        from src.agent.langfuse_client import _NullLangfuse

        langfuse = _NullLangfuse()
        trace = langfuse.trace(
            name="document_extraction",
            metadata={"document_id": "doc-123", "document_type": "application/pdf"},
        )
        span = trace.span(
            name="mistral_extraction", input={"model": "mistral-large-latest"}
        )
        span.end(output={"fields_extracted": 12, "confidence": 0.87})
        langfuse.flush()
