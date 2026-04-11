"""M-CTO-V53-H — politique Langfuse stricte optionnelle."""

from __future__ import annotations

import pytest


def test_langfuse_required_raises_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.agent.langfuse_client as lf

    lf._langfuse = None

    class _S:
        TESTING = False
        LANGFUSE_REQUIRED_FOR_LLM = True
        LANGFUSE_PUBLIC_KEY = ""
        LANGFUSE_SECRET_KEY = ""
        LANGFUSE_HOST = "https://cloud.langfuse.com"

    monkeypatch.setattr(lf, "get_settings", lambda: _S())

    with pytest.raises(RuntimeError, match="LANGFUSE_REQUIRED"):
        lf._build_langfuse()

    lf._langfuse = None


def test_langfuse_not_required_allows_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.agent.langfuse_client as lf

    class _S:
        TESTING = False
        LANGFUSE_REQUIRED_FOR_LLM = False
        LANGFUSE_PUBLIC_KEY = ""
        LANGFUSE_SECRET_KEY = ""
        LANGFUSE_HOST = "https://cloud.langfuse.com"

    monkeypatch.setattr(lf, "get_settings", lambda: _S())
    client = lf._build_langfuse()
    assert hasattr(client, "trace")
