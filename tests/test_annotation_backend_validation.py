"""
Tests backend _validate_and_correct — Couche 2 validation flow.
FALLBACK_RESPONSE (structure incomplète) → review_required=True.
Charge le backend via importlib (mistralai requis).
"""

from __future__ import annotations

import importlib.util
import os

import pytest

_BACKEND_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "services",
    "annotation-backend",
    "backend.py",
)


@pytest.fixture(autouse=True)
def _annotation_env(monkeypatch):
    """Isole les variables d'environnement requises par le backend — restaurées après chaque test."""
    monkeypatch.setenv("PSEUDONYM_SALT", "test-sel-validation-pytest")
    monkeypatch.setenv("ALLOW_WEAK_PSEUDONYMIZATION", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", os.environ.get("MISTRAL_API_KEY", ""))


def test_validate_fallback_returns_review_required():
    """FALLBACK_RESPONSE ne passe pas DMSAnnotation → review_required=True."""
    try:
        spec = importlib.util.spec_from_file_location("_backend_valid", _BACKEND_PATH)
        if spec is None:
            raise ImportError(f"spec_from_file_location returned None for path: {_BACKEND_PATH}")
        if spec.loader is None:
            raise ImportError(f"spec.loader is None for path: {_BACKEND_PATH} - cannot exec module")
        backend = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend)
    except Exception as e:
        pytest.skip(f"Backend import failed: {e}")

    result = backend._validate_and_correct(backend.FALLBACK_RESPONSE, task_id=0)
    assert result.get("_meta", {}).get("review_required") is True
    assert result.get("_meta", {}).get("annotation_status") == "review_required"
