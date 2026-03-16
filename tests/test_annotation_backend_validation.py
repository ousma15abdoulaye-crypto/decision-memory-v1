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

os.environ.setdefault("PSEUDONYM_SALT", "test-sel-validation-pytest")
os.environ.setdefault("ALLOW_WEAK_PSEUDONYMIZATION", "1")
os.environ.setdefault("MISTRAL_API_KEY", "")

try:
    _spec = importlib.util.spec_from_file_location("_backend_valid", _BACKEND_PATH)
    _backend = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_backend)
    FALLBACK_RESPONSE = _backend.FALLBACK_RESPONSE
    _validate_and_correct = _backend._validate_and_correct
    _BACKEND_LOADED = True
    _skip_reason = ""
except Exception as e:
    _BACKEND_LOADED = False
    _skip_reason = str(e)
    FALLBACK_RESPONSE = None
    _validate_and_correct = None


@pytest.mark.skipif(not _BACKEND_LOADED, reason=f"Backend import failed: {_skip_reason}")
def test_validate_fallback_returns_review_required():
    """FALLBACK_RESPONSE ne passe pas DMSAnnotation → review_required=True."""
    result = _validate_and_correct(FALLBACK_RESPONSE, task_id=0)
    assert result.get("_meta", {}).get("review_required") is True
    assert result.get("_meta", {}).get("annotation_status") == "review_required"
