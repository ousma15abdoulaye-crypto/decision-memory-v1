"""Context Store Redis — Canon V5.1.0 Section 7.8.

Stockage des sessions conversationnelles dans Redis avec TTL 3600s.
Sliding window FIFO : messages[-50:] sauvegardés.
Budget tokens : 8000 total, 1200 system, 2000 response -> 4800 historique.

Dégradation gracieuse si Redis non disponible : context en mémoire uniquement.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MQL_CONTEXT_TTL = 3600
MQL_CONTEXT_PREFIX = "mql:ctx:"

MAX_CONTEXT_TOKENS = 8000
SYSTEM_PROMPT_RESERVE = 1200
RESPONSE_RESERVE = 2000
HISTORY_BUDGET = MAX_CONTEXT_TOKENS - SYSTEM_PROMPT_RESERVE - RESPONSE_RESERVE

_redis: Any = None


async def _get_redis() -> Any:
    global _redis
    if _redis is None:
        try:
            import redis.asyncio as aioredis

            from src.core.config import get_settings

            _redis = aioredis.from_url(get_settings().REDIS_URL)
        except ImportError:
            logger.warning("redis.asyncio non disponible — context store en mémoire.")
            return None
    return _redis


@dataclass
class MQLContext:
    messages: list[dict[str, Any]] = field(default_factory=list)
    workspace_id: str | None = None

    def build_messages(
        self, system_prompt: str, user_query: str
    ) -> list[dict[str, str]]:
        """Construit la liste de messages pour le LLM.

        Applique la sliding window FIFO sur l'historique.
        """
        result: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        budget = HISTORY_BUDGET
        history_to_include: list[dict[str, Any]] = []

        for msg in reversed(self.messages):
            estimated_tokens = len(msg.get("content", "")) // 4
            if budget - estimated_tokens < 0:
                break
            history_to_include.insert(0, msg)
            budget -= estimated_tokens

        result.extend(history_to_include)
        result.append({"role": "user", "content": user_query})

        self.messages.append({"role": "user", "content": user_query})

        return result

    def add_assistant_message(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})


async def get_context(session_key: str) -> MQLContext:
    """Récupère le contexte depuis Redis. Fallback: contexte vide."""
    r = await _get_redis()
    if r is None:
        return MQLContext()

    key = MQL_CONTEXT_PREFIX + session_key
    try:
        data = await r.get(key)
        if data:
            parsed = json.loads(data)
            return MQLContext(
                messages=parsed.get("messages", []),
                workspace_id=parsed.get("workspace_id"),
            )
    except Exception as exc:
        logger.warning("Redis get_context failed: %s", exc)

    return MQLContext()


async def save_context(session_key: str, context: MQLContext) -> None:
    """Sauvegarde le contexte dans Redis avec TTL. messages[-50:] uniquement."""
    r = await _get_redis()
    if r is None:
        return

    key = MQL_CONTEXT_PREFIX + session_key
    data = json.dumps(
        {
            "messages": context.messages[-50:],
            "workspace_id": context.workspace_id,
        }
    )
    try:
        await r.setex(key, MQL_CONTEXT_TTL, data)
    except Exception as exc:
        logger.warning("Redis save_context failed: %s", exc)
