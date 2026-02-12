"""Rate limiting with slowapi."""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request
import logging

logger = logging.getLogger(__name__)

# Limiter configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Limite globale
    storage_uri="memory://"  # Utiliser Redis en production
)


def init_rate_limit(app: FastAPI):
    """Initialise rate limiting sur l'application."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting initialized (slowapi)")
