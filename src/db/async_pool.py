"""Pool de connexions asyncpg — DMS V4.2.0.

Utilisé exclusivement par les nouvelles routes workspace (W1/W2/W3),
le WebSocket, et le LangGraph AsyncPostgresSaver.

Référence : ADR-V420-004-CONNECTION-POOL.md
Allocation : 8 connexions asyncpg / 100 Railway Pro.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

_async_pool = None


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL manquant — pool async non initialisable.")
    # asyncpg exige postgresql:// (pas postgresql+psycopg://)
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if "postgresql+psycopg://" in url:
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


async def get_async_pool():
    """Retourne le pool asyncpg, l'initialise si nécessaire.

    Lazy — ne crashe pas à l'import.
    Pool min=2, max=8 (allocation ADR-V420-004).
    """
    global _async_pool
    if _async_pool is not None:
        return _async_pool

    try:
        import asyncpg  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("[DB-ASYNC-POOL] asyncpg non installé.")
        return None

    url = _get_database_url()
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


@asynccontextmanager
async def acquire_with_rls(
    tenant_id: str,
    is_admin: bool = False,
) -> AsyncGenerator:
    """Acquiert une connexion asyncpg avec SET LOCAL RLS — RÈGLE-W01.

    Usage réservé aux routes workspace V4.2.0.
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
            await conn.execute("SET LOCAL app.tenant_id = $1", str(tenant_id))
            if is_admin:
                await conn.execute("SET LOCAL app.is_admin = 'true'")
            yield conn
