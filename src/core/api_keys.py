"""
src/core/api_keys.py — Lazy API-key helpers.

Keys are read from environment variables ONLY when a tool actually calls
get_llama_cloud_api_key() or get_mistral_api_key().  Nothing is imported or
validated at module-load time, so the app starts normally even if the keys
are absent.

Environment variables (set in .env / .env.local — never commit real keys):
  LLAMA_CLOUD_API_KEY  — LlamaParse / LlamaCloud
  MISTRAL_API_KEY      — Mistral AI (OCR fallback + LLM extraction)
"""

from __future__ import annotations

import os


class APIKeyMissingError(RuntimeError):
    """Raised when a required API key is absent from the environment."""


def get_llama_cloud_api_key() -> str:
    """Return the LlamaParse / LlamaCloud API key.

    Reads LLAMA_CLOUD_API_KEY from the environment at call time.
    Raises APIKeyMissingError if the variable is not set or is empty.
    """
    key = os.environ.get("LLAMA_CLOUD_API_KEY", "").strip()
    if not key:
        raise APIKeyMissingError(
            "LLAMA_CLOUD_API_KEY is not set. "
            "Add it to your .env or .env.local file (see .env.example). "
            "Never commit the real key to the repository."
        )
    return key


def get_mistral_api_key() -> str:
    """Return the Mistral AI API key.

    Reads MISTRAL_API_KEY from the environment at call time.
    Raises APIKeyMissingError if the variable is not set or is empty.
    """
    key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not key:
        raise APIKeyMissingError(
            "MISTRAL_API_KEY is not set. "
            "Add it to your .env or .env.local file (see .env.example). "
            "Never commit the real key to the repository."
        )
    return key
