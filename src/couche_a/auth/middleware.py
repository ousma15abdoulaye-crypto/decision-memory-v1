"""Middleware sécurité V4.1.0 — headers + rate limiting Redis.

Deux middlewares indépendants :
  - SecurityHeadersMiddleware  : headers de sécurité sur toutes les réponses
  - RedisRateLimitMiddleware   : rate limiting Redis avec fallback no-op

RÈGLE-04 : Redis = cache reconstructible. Jamais source de vérité.
Terrain Mali : Redis peut être down → fallback no-op obligatoire.
"""

from __future__ import annotations

import logging
import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# ── Constantes rate limiting
_RATE_IP_LIMIT = 100
_RATE_USER_LIMIT = 200
_RATE_WINDOW_SECONDS = 60


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Ajoute les headers de sécurité sur toutes les réponses.

    Headers posés :
      X-Content-Type-Options     : nosniff
      X-Frame-Options            : DENY
      X-XSS-Protection           : 1; mode=block
      Strict-Transport-Security  : max-age=31536000; includeSubDomains
      Content-Security-Policy    : default-src 'self'
      Referrer-Policy            : strict-origin-when-cross-origin
      Cache-Control              : no-store  (routes /auth/* uniquement)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if request.url.path.startswith("/auth"):
            response.headers["Cache-Control"] = "no-store"

        return response


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting Redis — fenêtre glissante 60 secondes.

    Limites :
      rate:ip:{ip}       → 100 req/min par IP
      rate:user:{user_id}→ 200 req/min par user authentifié

    Fallback : si Redis absent ou erreur → log WARNING + requête passe.
    RÈGLE-04 : Redis = cache reconstructible. Jamais bloquer l'app.
    """

    def __init__(self, app, redis_url: str | None = None) -> None:
        super().__init__(app)
        self._redis_url = redis_url or os.environ.get(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        self._redis = None
        self._redis_unavailable = False

    def _get_redis(self):
        if self._redis_unavailable:
            return None
        if self._redis is not None:
            return self._redis
        try:
            import redis as redis_lib

            self._redis = redis_lib.from_url(self._redis_url, decode_responses=True)
            self._redis.ping()
            return self._redis
        except Exception as exc:
            _prod = os.environ.get("RAILWAY_ENVIRONMENT") == "production" or (
                os.environ.get("ENV", "").lower() == "production"
            )
            if _prod:
                logger.error(
                    "PROD — Redis indisponible : rate limiting en no-op. Erreur : %s",
                    exc,
                )
            else:
                logger.warning(
                    "Redis indisponible — rate limiting désactivé (fallback no-op). "
                    "Erreur : %s",
                    exc,
                )
            self._redis_unavailable = True
            self._redis = None
            return None

    def _check_limit(self, key: str, limit: int) -> tuple[bool, int]:
        """Vérifie la limite pour une clé.

        Returns:
            (is_allowed, retry_after_seconds)
        """
        r = self._get_redis()
        if r is None:
            return True, 0

        try:
            now = int(time.time())
            window_start = now - _RATE_WINDOW_SECONDS

            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now) + ":" + str(id(pipe)): now})
            pipe.zcard(key)
            pipe.expire(key, _RATE_WINDOW_SECONDS)
            results = pipe.execute()

            count = results[2]
            if count > limit:
                return False, _RATE_WINDOW_SECONDS
            return True, 0
        except Exception as exc:
            logger.warning("Erreur Redis rate limit — fallback no-op. Erreur : %s", exc)
            return True, 0

    def _extract_user_id(self, request: Request) -> str | None:
        """Extrait user_id depuis le JWT Bearer sans validation complète."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        try:
            from jose import jwt as _jwt

            payload = _jwt.get_unverified_claims(token)
            return payload.get("sub")
        except Exception:
            return None

    async def dispatch(self, request: Request, call_next) -> Response:
        ip = request.client.host if request.client else "unknown"
        ip_key = f"rate:ip:{ip}"

        allowed, retry_after = self._check_limit(ip_key, _RATE_IP_LIMIT)
        if not allowed:
            return Response(
                content='{"detail":"Too Many Requests"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(retry_after)},
            )

        user_id = self._extract_user_id(request)
        if user_id:
            user_key = f"rate:user:{user_id}"
            allowed, retry_after = self._check_limit(user_key, _RATE_USER_LIMIT)
            if not allowed:
                return Response(
                    content='{"detail":"Too Many Requests"}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(retry_after)},
                )

        return await call_next(request)
