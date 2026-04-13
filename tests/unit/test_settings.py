"""Tests unitaires — Pydantic Settings V5.2.

Vérifie le fail-fast, les validators, et l'isolation cache.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.core.config import Settings, get_settings, make_r2_s3_client

# Variables qui peuvent fuir depuis l'OS / .env.local et corrompre les défauts
_ISOLATE = [
    "TESTING",
    "LANGFUSE_HOST",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_BASE_URL",
    "JWT_SECRET",
    "REDIS_URL",
    "DMS_API_MISTRAL",
    "MISTRAL_HTTPX_VERIFY_SSL",
    "R2_ENDPOINT_URL",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_KEY",
    "R2_BUCKET_NAME",
    "S3_ENDPOINT",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_BUCKET",
]


def _base_env(monkeypatch, **overrides):
    """Pose les 3 variables required + overrides, et isole l'env du poste."""
    for var in _ISOLATE:
        monkeypatch.delenv(var, raising=False)
    defaults = {
        "DATABASE_URL": "postgresql://test:test@localhost/testdb",
        "SECRET_KEY": "a" * 32,
        "MISTRAL_API_KEY": "test-key",
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        monkeypatch.setenv(k, v)


def test_settings_fail_fast_missing_jwt_secret(monkeypatch):
    """Settings() sans SECRET_KEY ni JWT_SECRET -> ValidationError."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://x@localhost/db")
    monkeypatch.setenv("MISTRAL_API_KEY", "key")
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        Settings()


def test_settings_jwt_secret_min_32_chars(monkeypatch):
    """SECRET_KEY < 32 chars -> ValidationError."""
    monkeypatch.setenv("SECRET_KEY", "short")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x@localhost/db")
    monkeypatch.setenv("MISTRAL_API_KEY", "key")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        Settings()


def test_settings_testing_flag_accepts_string_true(monkeypatch):
    """TESTING = "true" (Railway/CI string) -> settings.TESTING is True."""
    _base_env(monkeypatch, TESTING="true")
    get_settings.cache_clear()
    s = Settings()
    assert s.TESTING is True


def test_settings_lru_cache_isolation_in_tests(monkeypatch):
    """cache_clear() permet l'isolation entre tests."""
    _base_env(monkeypatch, REDIS_URL="redis://custom:6380")
    get_settings.cache_clear()
    s1 = get_settings()
    assert s1.REDIS_URL == "redis://custom:6380"

    monkeypatch.setenv("REDIS_URL", "redis://other:6381")
    get_settings.cache_clear()
    s2 = get_settings()
    assert s2.REDIS_URL == "redis://other:6381"
    assert s1.REDIS_URL != s2.REDIS_URL


def test_settings_database_url_requires_postgresql_scheme(monkeypatch):
    """DATABASE_URL = "mysql://..." -> ValidationError."""
    _base_env(monkeypatch, DATABASE_URL="mysql://bad@localhost/db")
    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="postgresql"):
        Settings()


def test_settings_jwt_secret_alias_fallback(monkeypatch):
    """JWT_SECRET fournit SECRET_KEY si celui-ci est absent."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET", "b" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql://x@localhost/db")
    monkeypatch.setenv("MISTRAL_API_KEY", "key")
    get_settings.cache_clear()
    s = Settings()
    assert s.SECRET_KEY == "b" * 32


def test_settings_defaults(monkeypatch):
    """Vérifie les défauts des champs optionnels."""
    _base_env(monkeypatch)
    get_settings.cache_clear()
    s = Settings()
    assert s.TESTING is False
    assert s.REDIS_URL == "redis://localhost:6379"
    assert s.JWT_ACCESS_TTL_MINUTES == 30
    assert s.JWT_REFRESH_TTL_DAYS == 7
    assert s.DEFAULT_TENANT_CODE == "sci_mali"
    assert s.LANGFUSE_HOST == "https://cloud.langfuse.com"
    assert s.AGENT_RAG_ENABLED is False


def test_settings_r2_s3_env_aliases_resolve(monkeypatch):
    """Variables ``S3_*`` remplissent les champs R2 (AliasChoices)."""
    _base_env(
        monkeypatch,
        S3_ENDPOINT="https://acct.r2.cloudflarestorage.com",
        S3_ACCESS_KEY_ID="access-key",
        S3_SECRET_ACCESS_KEY="secret-key",
        S3_BUCKET="my-bucket",
    )
    get_settings.cache_clear()
    s = Settings()
    assert s.R2_ENDPOINT_URL == "https://acct.r2.cloudflarestorage.com"
    assert s.R2_ACCESS_KEY_ID == "access-key"
    assert s.R2_SECRET_KEY == "secret-key"
    assert s.R2_BUCKET_NAME == "my-bucket"


def test_settings_r2_object_storage_configured_via_s3_alias(monkeypatch):
    """r2_object_storage_configured() True quand les trois secrets sont via S3_*."""
    _base_env(
        monkeypatch,
        S3_ENDPOINT="https://x.r2.cloudflarestorage.com",
        S3_ACCESS_KEY_ID="k",
        S3_SECRET_ACCESS_KEY="s",
    )
    get_settings.cache_clear()
    s = Settings()
    assert s.r2_object_storage_configured() is True


def test_settings_r2_object_storage_configured_false_if_incomplete(monkeypatch):
    """Endpoint seul → pas de stockage R2 actif."""
    _base_env(
        monkeypatch,
        S3_ENDPOINT="https://x.r2.cloudflarestorage.com",
    )
    get_settings.cache_clear()
    s = Settings()
    assert s.r2_object_storage_configured() is False


def test_make_r2_s3_client_strips_trailing_slash_on_endpoint(monkeypatch):
    """Endpoint Railway avec slash final → normalisé pour boto3."""
    _base_env(
        monkeypatch,
        R2_ENDPOINT_URL="https://x.r2.cloudflarestorage.com/",
        R2_ACCESS_KEY_ID="k",
        R2_SECRET_KEY="s",
    )
    captured: dict = {}

    def fake_client(_service: str, **kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    # CI n’installe pas toujours boto3 ; éviter ``monkeypatch.setattr("boto3.client", ...)``
    # qui force un import réel du paquet.
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=fake_client))
    get_settings.cache_clear()
    make_r2_s3_client()
    assert captured["endpoint_url"] == "https://x.r2.cloudflarestorage.com"
