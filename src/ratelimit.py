"""
Rate limiting production-grade — DMS v4.1
ASAP-07 : Redis en production (remplace memory:// fixe)
ASAP-08 : limiter.limit natif restauré (suppression no-op ligne 63)
ADR-016 : docs/adr/ADR-016_rate_limiting_redis.md

DÉCOUVERTE AUDIT 2026-03-17 :
  La ligne `limiter.limit = conditional_limit` (ancienne L63)
  écrasait silencieusement la méthode limit() de slowapi.
  Tous les @limiter.limit() dans auth_router.py et routers.py
  étaient des no-ops depuis le début du projet.
  Cette ligne est supprimée. Le limiter natif reprend son rôle.

V5.2 : Variables d'environnement lues via get_settings() (Pydantic Settings).
"""

import logging
from urllib.parse import urlparse

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.core.config import get_settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# STORAGE — Redis prod / memory test
# ─────────────────────────────────────────────────────────────


def _resolve_storage() -> tuple[str, bool]:
    """Résout le backend de stockage et le flag TESTING depuis Settings."""
    s = get_settings()
    is_testing = s.TESTING
    redis_url = s.REDIS_URL.strip()

    if is_testing:
        logger.debug("[RATELIMIT] Mode test — memory://")
        return "memory://", True
    if redis_url:
        logger.info("[RATELIMIT] Redis — production mode")
        return redis_url, False

    logger.warning(
        "[RATELIMIT] REDIS_URL absent — fallback memory://. "
        "Rate limiting non persistant entre restarts. "
        "Configurer REDIS_URL en production (Railway Dashboard)."
    )
    return "memory://", False


_storage, _TESTING = _resolve_storage()

TESTING = _TESTING

# ─────────────────────────────────────────────────────────────
# LIMITER — natif slowapi — NE PAS RÉASSIGNER .limit
# (sauf en mode TESTING, où l'on désactive explicitement les limites)
# ─────────────────────────────────────────────────────────────

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage,
    default_limits=[] if _TESTING else ["100/minute"],
)

if _TESTING:

    def _noop_limit(*limit_args, **limit_kwargs):
        def decorator(func):
            return func

        return decorator

    limiter.limit = _noop_limit  # type: ignore[attr-defined]
    limiter.enabled = False  # type: ignore[attr-defined]
    logger.warning(
        "[RATELIMIT] TESTING=True — décorateurs @limiter.limit désactivés (no-op)"
    )

# ─────────────────────────────────────────────────────────────
# CONSTANTES LIMITES PAR CRITICITÉ — FIGÉES
# GO CTO obligatoire avant modification
# ─────────────────────────────────────────────────────────────

LIMIT_AUTH = "10/minute"
LIMIT_UPLOAD = "20/minute"
LIMIT_SCORING = "30/minute"
LIMIT_READ = "60/minute"
LIMIT_EXPORT = "5/minute"
LIMIT_ANNOTATION = "10/minute"


def route_limit(rate: str):
    """
    Décorateur rate limiting par route.
    Alias propre de limiter.limit() pour lisibilité.
    """
    return limiter.limit(rate)


def conditional_limit(*args, **kwargs):
    """
    SUPPRIMÉ — était un no-op dangereux (ASAP-08).
    Remplacer par @limiter.limit("X/minute")
    ou @route_limit(LIMIT_*).
    Ref : audit CTO senior 2026-03-17
    """
    raise RuntimeError(
        "conditional_limit supprimé (ASAP-08). "
        "Utiliser @limiter.limit('X/minute') "
        "ou @route_limit(LIMIT_AUTH/UPLOAD/...). "
        "Ref : ADR-016."
    )


def _describe_storage(storage: str) -> str:
    """
    Retourne une description non sensible du backend de stockage
    (type + éventuellement host/port), sans credentials.
    """
    if storage.startswith("memory://") or not storage:
        return "backend=memory"

    try:
        parsed = urlparse(storage)
    except Exception:
        return "backend=unknown"

    if not parsed.scheme:
        return "backend=unknown"

    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    hostport = f"{host}{port}" if (host or port) else ""

    if hostport:
        return f"backend={parsed.scheme} host={hostport}"

    return f"backend={parsed.scheme}"


def init_rate_limit(app: FastAPI):
    """Initialise rate limiting sur l'application."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    if _TESTING:
        logger.info(
            "[RATELIMIT] Mode test — décorateurs de rate limiting désactivés (memory://)"
        )
    else:
        safe_storage = _describe_storage(_storage)
        logger.info("[RATELIMIT] Initialized — %s", safe_storage)
