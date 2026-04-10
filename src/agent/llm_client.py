"""LLM Client avec Streaming — Canon V5.1.0 Section 7.6.

Client Mistral pour chat streaming.
Dégradation gracieuse si MISTRAL_API_KEY ou SDK absents.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from src.core.config import get_settings

logger = logging.getLogger(__name__)

_client: Any = None
_fallback = False


def _get_client() -> Any:
    global _client, _fallback

    if _client is not None:
        return _client

    api_key = get_settings().MISTRAL_API_KEY
    if not api_key:
        logger.warning("MISTRAL_API_KEY non définie — llm_client en mode fallback.")
        _fallback = True
        return None

    try:
        from mistralai import Mistral

        _client = Mistral(api_key=api_key)
        return _client
    except ImportError:
        logger.warning("mistralai non installé — llm_client en mode fallback.")
        _fallback = True
        return None


async def stream_mistral(
    model: str,
    messages: list[dict],
    langfuse_span: Any,
) -> AsyncGenerator[str, None]:
    """Stream les tokens depuis Mistral. Chaque token est yielded individuellement.

    En mode fallback, yielde un message statique.
    INV-A06 : failures are recorded in the circuit breaker.
    """
    from src.agent.circuit_breaker import get_breaker

    client = _get_client()
    breaker = get_breaker()

    if client is None or _fallback:
        fallback_msg = (
            "[Mode fallback — Mistral non configuré] "
            "Données de marché disponibles. Consultez les sources ci-dessus."
        )
        yield fallback_msg
        langfuse_span.update(
            output={"content_length": len(fallback_msg)},
            metadata={"usage": {"fallback": True}},
        )
        await breaker.record_failure()
        return
    full_content = ""
    usage: dict[str, Any] = {}

    try:
        response = await client.chat.stream_async(
            model=model,
            messages=messages,
        )

        async for chunk in response:
            if chunk.data.choices:
                delta = chunk.data.choices[0].delta
                if delta.content:
                    full_content += delta.content
                    yield delta.content

            if chunk.data.usage:
                usage = {
                    "input_tokens": chunk.data.usage.prompt_tokens,
                    "output_tokens": chunk.data.usage.completion_tokens,
                }

        await breaker.record_success()

    except Exception as exc:
        await breaker.record_failure()
        logger.error("Mistral streaming error (model=%s): %s", model, exc)
        langfuse_span.update(
            output={"error": str(exc)},
            level="ERROR",
        )
        raise

    langfuse_span.update(
        output={"content_length": len(full_content)},
        metadata={"usage": usage},
    )
