"""Normalisation du contenu assistant Mistral (SDK 1.5 : str ou chunks)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

_backend_dir = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _backend_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "PSEUDONYM_SALT", os.environ.get("PSEUDONYM_SALT", "test-sel-mistral-norm")
    )
    monkeypatch.setenv(
        "ALLOW_WEAK_PSEUDONYMIZATION",
        os.environ.get("ALLOW_WEAK_PSEUDONYMIZATION", "1"),
    )
    monkeypatch.setenv("MISTRAL_API_KEY", os.environ.get("MISTRAL_API_KEY", ""))


if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))


def _load_backend_module():
    path = _backend_dir / "backend.py"
    spec = importlib.util.spec_from_file_location("backend_mistral_norm", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mistral_message_content_to_str_plain_string() -> None:
    backend = _load_backend_module()
    assert backend._mistral_message_content_to_str('{"a":1}') == '{"a":1}'
    assert backend._mistral_message_content_to_str("") == ""
    assert backend._mistral_message_content_to_str(None) == ""


def test_mistral_message_content_to_str_list_of_dict_chunks() -> None:
    backend = _load_backend_module()
    chunks = [{"type": "text", "text": '{"x":'}, {"type": "text", "text": "true}"}]
    out = backend._mistral_message_content_to_str(chunks)
    assert json.loads(out) == {"x": True}


def test_mistral_message_content_to_str_list_of_textchunk_like() -> None:
    backend = _load_backend_module()

    class _Chunk:
        def __init__(self, text: str) -> None:
            self.text = text

    raw = backend._mistral_message_content_to_str([_Chunk('{"ok":'), _Chunk("true}")])
    assert json.loads(raw) == {"ok": True}


def test_parse_mistral_response_accepts_non_string_and_parses() -> None:
    backend = _load_backend_module()
    payload = {"couche_1_routing": {"taxonomy_core": "rfq"}}
    nested = [{"text": json.dumps(payload)}]
    parsed, ok = backend._parse_mistral_response(nested, task_id=42)
    assert ok is True
    assert parsed["couche_1_routing"]["taxonomy_core"] == "rfq"


def test_parse_mistral_response_invalid_returns_fallback_tuple() -> None:
    backend = _load_backend_module()
    parsed, ok = backend._parse_mistral_response("not json {{{", task_id=1)
    assert ok is False
    assert "AMBIG-PARSE_FAILED" in (parsed.get("ambiguites") or [])
