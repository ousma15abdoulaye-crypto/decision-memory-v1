"""Pool de connexions asyncpg — DMS V4.2.0.

Utilisé exclusivement par les nouvelles routes workspace (W1/W2/W3),
le WebSocket, et le LangGraph AsyncPostgresSaver.

Référence : ADR-V420-004-CONNECTION-POOL.md
Allocation : 8 connexions asyncpg / 100 Railway Pro.

RLS : SELECT set_config('app.tenant_id', $1, true) — aligné sur src/db/core.py.
      set_config(is_local=true) = scope transaction, réinitialisé auto (RÈGLE-W01).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)

_async_pool = None
_async_pool_lock: asyncio.Lock | None = None


def _get_database_url() -> str:
    """Normalise et valide DATABASE_URL — aligné sur src/db/core.py INV-4."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "Constitution INV-4 — DATABASE_URL manquant pour la connexion PostgreSQL."
        )
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)

    lowered = url.lower()
    if lowered.startswith("sqlite:"):
        raise RuntimeError(
            "Constitution INV-4 — SQLite n'est pas autorisé ; une URL PostgreSQL est requise."
        )
    if not lowered.startswith("postgresql://"):
        raise RuntimeError("Constitution INV-4 — DATABASE_URL doit cibler PostgreSQL.")
    return url


def _get_lock() -> asyncio.Lock:
    """Retourne (ou crée) le Lock asyncio pour la création du pool — thread-safe."""
    global _async_pool_lock
    if _async_pool_lock is None:
        _async_pool_lock = asyncio.Lock()
    return _async_pool_lock


async def get_async_pool():
    """Retourne le pool asyncpg, l'initialise si nécessaire.

    Lazy + coroutine-safe (double-check locking via asyncio.Lock).
    Pool min=2, max=8 (allocation ADR-V420-004).
    """
    global _async_pool
    if _async_pool is not None:
        return _async_pool

    async with _get_lock():
        if _async_pool is not None:
            return _async_pool

        try:
            import asyncpg  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("[DB-ASYNC-POOL] asyncpg non installé.")
            return None

        try:
            url = _get_database_url()
        except RuntimeError as exc:
            logger.warning("[DB-ASYNC-POOL] Pool non initialisé : %s", exc)
            return None

        _async_pool = await asyncpg.create_pool(
            dsn=url,
            min_size=2,
            max_size=8,
        )
        logger.info("[DB-ASYNC-POOL] Pool asyncpg initialisé (min=2, max=8).")
    return _async_pool


async def close_async_pool() -> None:
    """Ferme le pool asyncpg proprement (appel lifespan FastAPI)."""
    global _async_pool
    if _async_pool is not None:
        try:
            await _async_pool.close()
            logger.info("[DB-ASYNC-POOL] Pool asyncpg fermé.")
        except Exception as exc:
            logger.error("[DB-ASYNC-POOL] Erreur fermeture : %s", exc)
        finally:
            _async_pool = None


_NAMED_PARAM_RE = re.compile(r":([a-zA-Z_]\w*)")


def _convert_named_to_positional(
    sql: str, params: dict[str, Any]
) -> tuple[str, list[Any]]:
    """Convert :name style params to $N positional params for asyncpg."""
    seen: dict[str, int] = {}
    args: list[Any] = []

    def _replacer(m: re.Match) -> str:
        name = m.group(1)
        if name not in seen:
            args.append(params[name])
            seen[name] = len(args)
        return f"${seen[name]}"

    converted_sql = _NAMED_PARAM_RE.sub(_replacer, sql)
    return converted_sql, args


class AsyncpgAdapter:
    """Thin adapter wrapping asyncpg.Connection with :name param style.

    Bridges the gap between handler/engine code (psycopg :name style)
    and asyncpg ($N positional style).
    """

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def fetch_all(self, sql: str, params: dict[str, Any]) -> list[Any]:
        q, args = _convert_named_to_positional(sql, params)
        return await self._conn.fetch(q, *args)

    async def fetch_one(self, sql: str, params: dict[str, Any]) -> Any | None:
        q, args = _convert_named_to_positional(sql, params)
        return await self._conn.fetchrow(q, *args)

    async def fetch_val(self, sql: str, params: dict[str, Any]) -> Any | None:
        q, args = _convert_named_to_positional(sql, params)
        return await self._conn.fetchval(q, *args)

    async def execute(self, sql: str, params: dict[str, Any]) -> str:
        q, args = _convert_named_to_positional(sql, params)
        return await self._conn.execute(q, *args)


@asynccontextmanager
async def acquire_with_rls(
    tenant_id: str,
    is_admin: bool = False,
) -> AsyncGenerator:
    """Acquiert une connexion asyncpg avec RLS via set_config() — RÈGLE-W01.

    Utilise SELECT set_config('app.tenant_id', $1, true) (is_local=true),
    aligné sur src/db/core.py. Le scope est la transaction courante ;
    la valeur est réinitialisée automatiquement à la fin de la transaction,
    évitant toute fuite de tenant entre requêtes sur le pool.

    tenant_id provient exclusivement du JWT décodé (jamais query/body).

    Args:
        tenant_id: UUID tenant extrait du JWT.
        is_admin: True si le claim JWT is_admin est vrai.

    Yields:
        asyncpg.Connection avec RLS configuré.
    """
    pool = await get_async_pool()
    if pool is None:
        raise RuntimeError("Pool asyncpg non disponible — asyncpg non installé.")

    async with pool.acquire() as conn:
        async with conn.transaction():
            # set_config avec is_local=true — scope transaction (RÈGLE-W01)
            await conn.execute(
                "SELECT set_config('app.tenant_id', $1, true)", str(tenant_id)
            )
            await conn.execute(
                "SELECT set_config('app.current_tenant', $1, true)", str(tenant_id)
            )
            if is_admin:
                await conn.execute("SELECT set_config('app.is_admin', 'true', true)")
            yield conn
