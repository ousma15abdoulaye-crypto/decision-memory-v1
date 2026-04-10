"""Pool de connexions psycopg synchrone — DMS V4.2.0.

Prépare l'introduction d'un pool partagé pour les routes FastAPI existantes.
Les nouvelles routes workspace utilisent asyncpg (src/db/async_pool.py).

Référence : ADR-V420-004-CONNECTION-POOL.md
Allocation cible : 10 connexions FastAPI / 100 Railway Pro.

Note : src/db/core.py utilise encore psycopg.connect() direct.
       L'intégration progressive de get_pool() dans core.py est prévue
       en Phase 3 (migration workspace_id complète).
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_pool = None
_pool_lock = threading.Lock()


def _get_database_url() -> str:
    """Normalise et valide DATABASE_URL — aligné sur src/db/core.py INV-4."""
    from src.core.config import get_settings

    url = get_settings().DATABASE_URL.strip()
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


def get_pool():
    """Retourne le pool psycopg synchrone, l'initialise si nécessaire.

    Lazy + thread-safe (double-check locking).
    Pool min=2, max=10 (allocation ADR-V420-004).
    Ne crashe pas à l'import si DATABASE_URL absent ou psycopg_pool manquant.
    """
    global _pool
    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        try:
            from psycopg_pool import ConnectionPool  # type: ignore[import-untyped]
        except ImportError:
            logger.warning(
                "[DB-POOL] psycopg_pool non installé — utilisation connexions individuelles."
            )
            return None

        try:
            url = _get_database_url()
        except RuntimeError as exc:
            logger.warning("[DB-POOL] Pool non initialisé : %s", exc)
            return None

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
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.close()
                logger.info("[DB-POOL] Pool psycopg fermé.")
            except Exception as exc:
                logger.error("[DB-POOL] Erreur fermeture pool : %s", exc)
            finally:
                _pool = None
