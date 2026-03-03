# tests/phase0/test_api_keys.py
"""
Tests unitaires — src/core/api_keys.py
🔴 BLOQUANTS CI.
Vérifie le contrat env-var lazy-load pour LlamaParse et Mistral.
"""

import pytest

from src.core.api_keys import (
    APIKeyMissingError,
    get_llama_cloud_api_key,
    get_mistral_api_key,
)


# ── Classe 1 — get_llama_cloud_api_key ──────────────────────────


class TestGetLlamaCloudApiKey:
    """LLAMA_CLOUD_API_KEY : lazy-load + validation."""

    def test_absent_raises_api_key_missing_error(self, monkeypatch):
        """Variable absente → APIKeyMissingError."""
        monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)
        with pytest.raises(APIKeyMissingError) as exc:
            get_llama_cloud_api_key()
        assert "LLAMA_CLOUD_API_KEY" in str(exc.value)

    def test_empty_raises_api_key_missing_error(self, monkeypatch):
        """Variable vide → APIKeyMissingError."""
        monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "")
        with pytest.raises(APIKeyMissingError):
            get_llama_cloud_api_key()

    def test_whitespace_only_raises_api_key_missing_error(self, monkeypatch):
        """Variable = espaces uniquement → APIKeyMissingError."""
        monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "   \t  ")
        with pytest.raises(APIKeyMissingError):
            get_llama_cloud_api_key()

    def test_valid_key_returned_stripped(self, monkeypatch):
        """Variable définie avec espaces → retournée sans espaces."""
        monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "  llx-test-key-123  ")
        result = get_llama_cloud_api_key()
        assert result == "llx-test-key-123"

    def test_valid_key_returned(self, monkeypatch):
        """Variable définie → retournée telle quelle."""
        monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "llx-real-key")
        assert get_llama_cloud_api_key() == "llx-real-key"

    def test_error_message_actionable(self, monkeypatch):
        """Message d'erreur contient la variable et le fichier .env."""
        monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)
        with pytest.raises(APIKeyMissingError) as exc:
            get_llama_cloud_api_key()
        msg = str(exc.value)
        assert "LLAMA_CLOUD_API_KEY" in msg
        assert ".env" in msg


# ── Classe 2 — get_mistral_api_key ──────────────────────────────


class TestGetMistralApiKey:
    """MISTRAL_API_KEY : lazy-load + validation."""

    def test_absent_raises_api_key_missing_error(self, monkeypatch):
        """Variable absente → APIKeyMissingError."""
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        with pytest.raises(APIKeyMissingError) as exc:
            get_mistral_api_key()
        assert "MISTRAL_API_KEY" in str(exc.value)

    def test_empty_raises_api_key_missing_error(self, monkeypatch):
        """Variable vide → APIKeyMissingError."""
        monkeypatch.setenv("MISTRAL_API_KEY", "")
        with pytest.raises(APIKeyMissingError):
            get_mistral_api_key()

    def test_whitespace_only_raises_api_key_missing_error(self, monkeypatch):
        """Variable = espaces uniquement → APIKeyMissingError."""
        monkeypatch.setenv("MISTRAL_API_KEY", "   ")
        with pytest.raises(APIKeyMissingError):
            get_mistral_api_key()

    def test_valid_key_returned_stripped(self, monkeypatch):
        """Variable définie avec espaces → retournée sans espaces."""
        monkeypatch.setenv("MISTRAL_API_KEY", "  sk-mistral-test  ")
        result = get_mistral_api_key()
        assert result == "sk-mistral-test"

    def test_valid_key_returned(self, monkeypatch):
        """Variable définie → retournée telle quelle."""
        monkeypatch.setenv("MISTRAL_API_KEY", "sk-mistral-real")
        assert get_mistral_api_key() == "sk-mistral-real"

    def test_error_message_actionable(self, monkeypatch):
        """Message d'erreur contient la variable et le fichier .env."""
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        with pytest.raises(APIKeyMissingError) as exc:
            get_mistral_api_key()
        msg = str(exc.value)
        assert "MISTRAL_API_KEY" in msg
        assert ".env" in msg


# ── Classe 3 — APIKeyMissingError est RuntimeError ──────────────


class TestAPIKeyMissingErrorType:
    """APIKeyMissingError hérite de RuntimeError (jamais silencieux §9)."""

    def test_is_runtime_error(self):
        assert issubclass(APIKeyMissingError, RuntimeError)

    def test_instance_of_runtime_error(self):
        err = APIKeyMissingError("test")
        assert isinstance(err, RuntimeError)
