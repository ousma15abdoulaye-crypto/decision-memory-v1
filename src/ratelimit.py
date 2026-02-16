"""Rate limiting with slowapi."""
import logging
import os

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Check if we're in test mode
TESTING = os.getenv("TESTING", "false").lower() == "true"

# Limiter configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[] if TESTING else ["100/minute"],  # Disable in tests
    storage_uri="memory://"  # Utiliser Redis en production
)


def init_rate_limit(app: FastAPI):
    """Initialise rate limiting sur l'application."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    if TESTING:
        logger.info("Rate limiting DISABLED (test mode)")
    else:
        logger.info("Rate limiting initialized (slowapi)")


# Export original limiter but also provide conditional decorator
_original_limit = limiter.limit


def conditional_limit(rate_limit: str):
    """Conditional rate limiting - disabled in test mode.
    
    Note: In test mode, we return the original function unchanged,
    which naturally preserves all function metadata (name, docstring, signature).
    No need for @wraps since we're not creating a wrapper.
    """
    def decorator(func):
        if TESTING:
            # In test mode, return original function unchanged (preserves async + metadata)
            return func
        else:
            # In production, apply the rate limit
            return _original_limit(rate_limit)(func)
    return decorator


# Replace limiter.limit with our conditional version
limiter.limit = conditional_limit
