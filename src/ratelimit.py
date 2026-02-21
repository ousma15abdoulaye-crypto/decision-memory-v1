"""Rate limiting with slowapi."""

import logging
import os
from functools import wraps

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def _is_testing() -> bool:
    """Lit l'env var au moment de l'appel — jamais figé au chargement du module."""
    return os.environ.get("TESTING", "false").lower() == "true"


# Backward-compat export : True uniquement si TESTING est déjà posé avant cet import
# (garantie par tests/conftest.py → os.environ.setdefault("TESTING", "true"))
TESTING = _is_testing()

# Limiter configuration — default_limits évalué au chargement, mais après conftest
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[] if _is_testing() else ["100/minute"],
    storage_uri="memory://",  # Utiliser Redis en production
)


def init_rate_limit(app: FastAPI):
    """Initialise rate limiting sur l'application."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    if _is_testing():
        logger.info("Rate limiting DISABLED (test mode)")
    else:
        logger.info("Rate limiting initialized (slowapi)")


# Export original limiter but also provide conditional decorator
_original_limit = limiter.limit


def conditional_limit(rate_limit: str):
    """Décorateur rate-limit conditionnel.

    TESTING=true  → no-op (retourne func tel quel — préserve async + metadata).
    PROD          → comportement SlowAPI normal.

    _is_testing() est appelé au moment où le décorateur est appliqué
    (import du module décoré), pas au chargement de ratelimit.py.
    """

    def decorator(func):
        if _is_testing():
            # no-op : fonction originale inchangée (async, __name__, __doc__ préservés)
            return func

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return _original_limit(rate_limit)(wrapper)

    return decorator


# Replace limiter.limit with our conditional version
limiter.limit = conditional_limit
