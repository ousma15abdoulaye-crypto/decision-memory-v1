"""Pool de connexions psycopg synchrone — DMS V4.2.0.

Remplace les connexions individuelles psycopg pour les routes FastAPI existantes.
Les nouvelles routes workspace utilisent asyncpg (src/db/async_pool.py).

Référence : ADR-V420-004-CONNECTION-POOL.md
Allocation : 10 connexions FastAPI / 100 Railway Pro.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_pool = None


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL manquant — pool sync non initialisable.")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if "postgresql+psycopg://" in url:
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def get_pool():
    """Retourne le pool psycopg synchrone, l'initialise si nécessaire.

    Lazy — ne crashe pas à l'import si DATABASE_URL absent.
    Pool min=2, max=10 (allocation ADR-V420-004).
    """
    global _pool
    if _pool is not None:
        return _pool

    try:
        from psycopg_pool import ConnectionPool  # type: ignore[import-untyped]
    except ImportError:
        logger.warning(
            "[DB-POOL] psycopg_pool non installé — utilisation connexions individuelles."
        )
        return None

    url = _get_database_url()
    _pool = ConnectionPool(
        conninfo=url,
        min_size=2,
        max_size=10,
        open=True,
    )
    logger.info("[DB-POOL] Pool psycopg initialisé (min=2, max=10).")
    return _pool


def close_pool() -> None:
    """Ferme le pool proprement (appel lifespan FastAPI)."""
    global _pool
    if _pool is not None:
        try:
            _pool.close()
            logger.info("[DB-POOL] Pool psycopg fermé.")
        except Exception as exc:
            logger.error("[DB-POOL] Erreur fermeture pool : %s", exc)
        finally:
            _pool = None
