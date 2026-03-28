# tests/phase0/test_api_keys.py
"""
Tests unitaires — src/core/api_keys.py
M-EXTRACTION-ENGINE — contrat env-var lazy-load.
🔴 BLOQUANTS CI.
Constitution V3.3.2 §9 (doctrine échec — jamais silencieux).
ADR-0002 §2.5 (SLA deux classes — clés lues à l'appel, pas au boot).

Vérifie :
  (1) variable absente / chaîne vide / whitespace-only → APIKeyMissingError
  (2) espaces autour de la clé → strip() appliqué
  (3) message d'erreur contient le nom de l'env-var + .env
  (4) APIKeyMissingError hérite de RuntimeError (§9 : jamais silencieux)
  (5) lazy-load : aucune clé lue à l'import (pas de side-effect au chargement)
"""

from __future__ import annotations

import pytest

from src.core.api_keys import (
    APIKeyMissingError,
    get_llama_cloud_api_key,
    get_mistral_api_key,
)

# ── Classe 1 — get_llama_cloud_api_key ──────────────────────────


def _clear_llama_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLAMADMS", raising=False)
    monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)


class TestGetLlamaCloudApiKey:
    """LLAMADMS + LLAMA_CLOUD_API_KEY : lazy-load + validation."""

    def test_absent_raises_api_key_missing_error(self, monkeypatch):
        """Les deux variables absentes → APIKeyMissingError."""
        _clear_llama_keys(monkeypatch)
        with pytest.raises(APIKeyMissingError, match="LLAMADMS"):
            get_llama_cloud_api_key()

    def test_empty_raises_api_key_missing_error(self, monkeypatch):
        """Les deux vides → APIKeyMissingError."""
        _clear_llama_keys(monkeypatch)
        monkeypatch.setenv("LLAMADMS", "")
        monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "")
        with pytest.raises(APIKeyMissingError, match="LLAMA_CLOUD_API_KEY"):
            get_llama_cloud_api_key()

    def test_whitespace_only_raises_api_key_missing_error(self, monkeypatch):
        """Les deux = espaces uniquement → APIKeyMissingError (strip appliqué)."""
        _clear_llama_keys(monkeypatch)
        monkeypatch.setenv("LLAMADMS", "   \t  ")
        monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "   \t  ")
        with pytest.raises(APIKeyMissingError):
            get_llama_cloud_api_key()

    def test_valid_key_returned_stripped(self, monkeypatch):
        """LLAMA_CLOUD_API_KEY avec espaces → retournée sans espaces."""
        _clear_llama_keys(monkeypatch)
        monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "  llx-test-key-123  ")
        result = get_llama_cloud_api_key()
        assert result == "llx-test-key-123"

    def test_valid_key_returned(self, monkeypatch):
        """LLAMA_CLOUD_API_KEY définie → retournée."""
        _clear_llama_keys(monkeypatch)
        monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "llx-real-key")
        assert get_llama_cloud_api_key() == "llx-real-key"

    def test_llamadms_alone_works(self, monkeypatch):
        """LLAMADMS seul (Railway) → retourné."""
        _clear_llama_keys(monkeypatch)
        monkeypatch.setenv("LLAMADMS", "  llx-from-railway  ")
        assert get_llama_cloud_api_key() == "llx-from-railway"

    def test_llamadms_precedence_over_llama_cloud(self, monkeypatch):
        """LLAMADMS prime sur LLAMA_CLOUD_API_KEY."""
        monkeypatch.setenv("LLAMADMS", "llx-primary")
        monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "llx-secondary")
        assert get_llama_cloud_api_key() == "llx-primary"

    def test_error_message_contains_env_ref(self, monkeypatch):
        """§9 : message d'erreur cite les variables ET .env."""
        _clear_llama_keys(monkeypatch)
        with pytest.raises(APIKeyMissingError) as exc:
            get_llama_cloud_api_key()
        msg = str(exc.value)
        assert "LLAMADMS" in msg
        assert "LLAMA_CLOUD_API_KEY" in msg
        assert ".env" in msg

    def test_error_warns_never_commit(self, monkeypatch):
        """§9 : message d'erreur rappelle de ne jamais commiter la clé."""
        _clear_llama_keys(monkeypatch)
        with pytest.raises(APIKeyMissingError, match="commit"):
            get_llama_cloud_api_key()


# ── Classe 2 — get_mistral_api_key ──────────────────────────────


class TestGetMistralApiKey:
    """MISTRAL_API_KEY : lazy-load + validation."""

    def test_absent_raises_api_key_missing_error(self, monkeypatch):
        """Variable absente → APIKeyMissingError."""
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        with pytest.raises(APIKeyMissingError, match="MISTRAL_API_KEY"):
            get_mistral_api_key()

    def test_empty_raises_api_key_missing_error(self, monkeypatch):
        """Variable vide → APIKeyMissingError."""
        monkeypatch.setenv("MISTRAL_API_KEY", "")
        with pytest.raises(APIKeyMissingError, match="MISTRAL_API_KEY"):
            get_mistral_api_key()

    def test_whitespace_only_raises_api_key_missing_error(self, monkeypatch):
        """Variable = espaces uniquement → APIKeyMissingError (strip appliqué)."""
        monkeypatch.setenv("MISTRAL_API_KEY", "   ")
        with pytest.raises(APIKeyMissingError):
            get_mistral_api_key()

    def test_valid_key_returned_stripped(self, monkeypatch):
        """Variable définie avec espaces → retournée sans espaces."""
        # Placeholder volontairement non réaliste — ne jamais committer de vraie clé.
        monkeypatch.setenv(
            "MISTRAL_API_KEY",
            "  sk-mistral-TEST_FAKE_PLACEHOLDER_NOT_A_SECRET  ",
        )
        result = get_mistral_api_key()
        assert result == "sk-mistral-TEST_FAKE_PLACEHOLDER_NOT_A_SECRET"

    def test_valid_key_returned(self, monkeypatch):
        """Variable définie → retournée telle quelle."""
        # Exemple factice pour pytest — pas une clé Mistral réelle.
        fake = "sk-mistral-REPLACE_ME_FAKE_KEY_FOR_TESTS_ONLY"
        monkeypatch.setenv("MISTRAL_API_KEY", fake)
        assert get_mistral_api_key() == fake

    def test_error_message_contains_env_ref(self, monkeypatch):
        """§9 : message d'erreur contient le nom de la variable ET .env."""
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        with pytest.raises(APIKeyMissingError) as exc:
            get_mistral_api_key()
        msg = str(exc.value)
        assert "MISTRAL_API_KEY" in msg
        assert ".env" in msg

    def test_error_warns_never_commit(self, monkeypatch):
        """§9 : message d'erreur rappelle de ne jamais commiter la clé."""
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        with pytest.raises(APIKeyMissingError, match="commit"):
            get_mistral_api_key()


# ── Classe 3 — APIKeyMissingError est RuntimeError ──────────────


class TestAPIKeyMissingErrorType:
    """APIKeyMissingError hérite de RuntimeError (§9 : jamais silencieux)."""

    def test_is_runtime_error(self):
        """APIKeyMissingError est sous-classe de RuntimeError."""
        assert issubclass(APIKeyMissingError, RuntimeError)

    def test_instance_of_runtime_error(self):
        """Instance concrète capturée par except RuntimeError."""
        err = APIKeyMissingError("test")
        assert isinstance(err, RuntimeError)


# ── Classe 4 — Lazy-load (pas de side-effect au chargement) ─────


class TestLazyLoadContract:
    """Contrat lazy-load : aucune clé lue au moment de l'import."""

    def test_import_sans_env_vars_ne_leve_pas(self, monkeypatch):
        """Import du module sans clés dans l'env → aucune exception."""
        monkeypatch.delenv("LLAMADMS", raising=False)
        monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        # Reload ici (pas en top-level) pour forcer un re-import frais
        import importlib

        import src.core.api_keys as mod

        importlib.reload(mod)
        # Module chargé sans exception → lazy-load confirmé
        assert hasattr(mod, "get_llama_cloud_api_key")
        assert hasattr(mod, "get_mistral_api_key")

    def test_getters_are_callable(self):
        """Les helpers sont des callables (pas des valeurs résolues au boot)."""
        assert callable(get_llama_cloud_api_key)
        assert callable(get_mistral_api_key)
