"""Lecture clé Mistral : DMS_API_MISTRAL (Railway) vs MISTRAL_API_KEY."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_backend_dir = Path(__file__).resolve().parents[1]
_repo_root = Path(__file__).resolve().parents[3]
for _p in (str(_backend_dir), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _load_backend_fresh(module_name: str) -> object:
    path = _backend_dir / "backend.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _env_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PSEUDONYM_SALT", "test-sel-env-keys")
    monkeypatch.setenv("ALLOW_WEAK_PSEUDONYMIZATION", "1")


def test_dms_api_mistral_used_when_mistral_api_key_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.setenv("DMS_API_MISTRAL", "key-from-dms-env")
    mod = _load_backend_fresh("backend_dms_mistral_only")
    assert mod.MISTRAL_API_KEY == "key-from-dms-env"


def test_mistral_api_key_wins_over_dms_api_mistral(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MISTRAL_API_KEY", "primary-key")
    monkeypatch.setenv("DMS_API_MISTRAL", "secondary-key")
    mod = _load_backend_fresh("backend_mistral_precedence")
    assert mod.MISTRAL_API_KEY == "primary-key"


def test_dms_api_mistral_strips_newlines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.setenv("DMS_API_MISTRAL", "abc\ndef\r\n")
    mod = _load_backend_fresh("backend_dms_trim")
    assert mod.MISTRAL_API_KEY == "abcdef"
