"""Langfuse client V5.1.0 — singleton thread-safe.

INV-A01 : tout appel LLM est tracé dans Langfuse.
Canon V5.1.0 Section 9.1.

Dégradation gracieuse si Langfuse n'est pas configuré :
  - LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY absents → _NullTrace (no-op)
  - Langfuse SDK absent → _NullTrace
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class _NullSpan:
    """Span no-op — trace désactivée."""

    def end(self, output: dict[str, Any] | None = None, **kwargs: Any) -> None:
        pass


class _NullTrace:
    """Trace no-op — Langfuse non configuré ou SDK absent."""

    def span(
        self, name: str, input: dict[str, Any] | None = None, **kwargs: Any
    ) -> _NullSpan:
        return _NullSpan()

    def update(self, **kwargs: Any) -> None:
        pass

    @property
    def id(self) -> str | None:
        return None


class _NullLangfuse:
    """Client Langfuse no-op."""

    def trace(
        self, name: str, metadata: dict[str, Any] | None = None, **kwargs: Any
    ) -> _NullTrace:
        return _NullTrace()

    def flush(self) -> None:
        pass


_langfuse: Any = None


def _build_langfuse() -> Any:
    """Construit le client Langfuse ou un no-op si non configuré."""
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()

    if not public_key or not secret_key:
        logger.info("[Langfuse] Clés absentes — traçage désactivé (mode no-op).")
        return _NullLangfuse()

    try:
        from langfuse import Langfuse  # type: ignore[import-untyped]

        host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        logger.info("[Langfuse] Client initialisé (host=%s).", host)
        return client
    except ImportError:
        logger.warning("[Langfuse] SDK non installé — traçage désactivé.")
        return _NullLangfuse()
    except Exception as exc:
        logger.error("[Langfuse] Erreur init : %s — traçage désactivé.", exc)
        return _NullLangfuse()


def get_langfuse() -> Any:
    """Retourne le client Langfuse singleton.

    INV-A01 : tout appel LLM est tracé.
    Configuration via LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST.
    Dégradation gracieuse si non configuré.
    """
    global _langfuse
    if _langfuse is None:
        _langfuse = _build_langfuse()
    return _langfuse


def flush_langfuse() -> None:
    """Flush les traces en attente.

    Appelé à la fin de chaque requête agent (Canon Section 9.1).
    """
    global _langfuse
    if _langfuse is not None:
        try:
            _langfuse.flush()
        except Exception as exc:
            logger.warning("[Langfuse] Erreur flush : %s", exc)
