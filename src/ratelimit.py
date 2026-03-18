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
"""

import logging
import os

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# STORAGE — Redis prod / memory test
# ─────────────────────────────────────────────────────────────

_REDIS_URL = os.environ.get("REDIS_URL", "")
_TESTING = os.environ.get("TESTING", "false").lower() == "true"

# Backward-compat : tests/conftest + test_upload_security importent TESTING
TESTING = _TESTING

if _TESTING:
    _storage = "memory://"
    logger.debug("[RATELIMIT] Mode test — memory://")
elif _REDIS_URL:
    _storage = _REDIS_URL
    logger.info("[RATELIMIT] Redis — production mode")
else:
    _storage = "memory://"
    logger.warning(
        "[RATELIMIT] REDIS_URL absent — fallback memory://. "
        "Rate limiting non persistant entre restarts. "
        "Configurer REDIS_URL en production (Railway Dashboard)."
    )

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
    # En mode TESTING, on rend limiter.limit no-op pour éviter que
    # les limites par IP (get_remote_address) soient mutualisées
    # entre tous les tests et provoquent des 429 aléatoires en CI.
    def _noop_limit(*limit_args, **limit_kwargs):
        def decorator(func):
            return func
        return decorator

    # Désactivation effec­tive des décorateurs @limiter.limit / @route_limit
    limiter.limit = _noop_limit  # type: ignore[attr-defined]
    # Attribut indicatif (ne change rien au comportement slowapi)
    limiter.enabled = False  # type: ignore[attr-defined]
    logger.warning(
        "[RATELIMIT] TESTING=True — décorateurs @limiter.limit désactivés (no-op)"
    )

# SUPPRIMÉ — était un no-op qui écrasait limiter.limit :
# limiter.limit = conditional_limit  ← LIGNE SUPPRIMÉE

# ─────────────────────────────────────────────────────────────
# CONSTANTES LIMITES PAR CRITICITÉ — FIGÉES
# GO CTO obligatoire avant modification
# ─────────────────────────────────────────────────────────────

LIMIT_AUTH = "10/minute"  # auth — cible brute-force
LIMIT_UPLOAD = "20/minute"  # upload — CPU intensif
LIMIT_SCORING = "30/minute"  # scoring — calcul intensif
LIMIT_READ = "60/minute"  # lecture standard
LIMIT_EXPORT = "5/minute"  # export — fichiers lourds
LIMIT_ANNOTATION = "10/minute"  # annotation — coût API LLM


def route_limit(rate: str):
    """
    Décorateur rate limiting par route.
    Alias propre de limiter.limit() pour lisibilité.

    Usage :
        @router.post("/upload")
        @route_limit(LIMIT_UPLOAD)
        async def upload(request: Request, ...):
            ...
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


def init_rate_limit(app: FastAPI):
    """Initialise rate limiting sur l'application."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    if _TESTING:
        logger.info(
            "[RATELIMIT] Mode test — décorateurs de rate limiting désactivés (memory://)"
        )
    else:
        logger.info(
            "[RATELIMIT] Initialized — storage=%s",
            _storage[:20] + "..." if len(_storage) > 20 else _storage,
        )
