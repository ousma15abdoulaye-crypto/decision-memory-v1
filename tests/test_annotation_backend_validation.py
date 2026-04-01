"""
Tests backend _validate_and_correct — Couche 2 validation flow.
FALLBACK_RESPONSE : squelette contractuel valide + review_required (parse/API KO).
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


def _load_backend(monkeypatch, cors_origins: str | None = None):
    """Charge le module backend avec l'env CORS_ORIGINS demandé."""
    import importlib
    import sys

    if cors_origins is not None:
        monkeypatch.setenv("CORS_ORIGINS", cors_origins)
    else:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)

    mod_name = f"_backend_cors_{id(cors_origins)}"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    spec = importlib.util.spec_from_file_location(mod_name, _BACKEND_PATH)
    backend = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(backend)
    except Exception as e:
        pytest.skip(f"Backend import failed: {e}")
    return backend


def test_validate_fallback_returns_review_required():
    """FALLBACK_RESPONSE : _meta review_required et statut review_required inchangés."""
    try:
        spec = importlib.util.spec_from_file_location("_backend_valid", _BACKEND_PATH)
        backend = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend)
    except Exception as e:
        pytest.skip(f"Backend import failed: {e}")

    annotation, errors = backend._validate_and_correct(
        backend.FALLBACK_RESPONSE, task_id=0
    )
    assert annotation.get("_meta", {}).get("review_required") is True
    assert annotation.get("_meta", {}).get("annotation_status") == "review_required"


def test_cors_wildcard_falls_back_to_localhost(monkeypatch, caplog):
    """CORS_ORIGINS='*' doit être rejeté et remplacé par localhost:8080."""
    import logging

    with caplog.at_level(logging.CRITICAL):
        backend = _load_backend(monkeypatch, cors_origins="*")

    assert backend.CORS_ORIGINS == [
        "http://localhost:8080"
    ], "Wildcard doit retomber sur localhost:8080"
    assert any(
        "CORS_ORIGINS='*' est interdit" in r.message for r in caplog.records
    ), "Un log CRITICAL doit être émis pour le wildcard CORS"


def test_cors_wildcard_type_is_list(monkeypatch):
    """CORS_ORIGINS doit toujours être list[str] — même en cas de wildcard."""
    backend = _load_backend(monkeypatch, cors_origins="*")
    assert isinstance(backend.CORS_ORIGINS, list)
    assert all(isinstance(o, str) for o in backend.CORS_ORIGINS)


def test_cors_explicit_origins_parsed(monkeypatch):
    """Plusieurs origines séparées par virgule doivent être correctement parsées."""
    backend = _load_backend(
        monkeypatch,
        cors_origins="https://app.example.com,https://label.example.com",
    )
    assert backend.CORS_ORIGINS == [
        "https://app.example.com",
        "https://label.example.com",
    ]
