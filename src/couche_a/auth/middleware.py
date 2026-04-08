"""Middleware sécurité V4.1.0 — headers + rate limiting Redis + tenant context.

Trois middlewares indépendants :
  - SecurityHeadersMiddleware  : headers de sécurité sur toutes les réponses
  - RedisRateLimitMiddleware   : rate limiting Redis avec fallback no-op
  - TenantContextMiddleware    : pose app.tenant_id / app.is_admin pour RLS
                                 sur TOUTE requête authentifiée (JWT sans
                                 vérification complète — lecture claims seule)

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


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Pose app.tenant_id et app.is_admin dans le contexte de la requête.

    Lit les claims JWT sans vérification cryptographique (pas de secret requis
    ici — la validation complète est déléguée à get_current_user). Ce middleware
    sert uniquement à exposer le tenant_id pour le RLS sur TOUTE requête
    authentifiée, y compris celles qui n'appellent pas get_current_user.

    Comportement :
    - Pas de Bearer → no-op (requête anonyme ou health check).
    - Bearer présent + claims lisibles → pose tenant_id / is_admin.
    - Lecture échoue → no-op + log WARNING (jamais bloquer).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            try:
                from jose import jwt as _jwt

                # SÉCURITÉ : get_unverified_claims() ne vérifie PAS la signature.
                # Ne jamais positionner app.is_admin depuis des claims non vérifiés —
                # un attaquant pourrait forger is_admin=true et bypasser l'isolation RLS.
                # app.is_admin est forcé à False ici ; seul get_current_user() (qui
                # vérifie la signature) doit le promouvoir via set_rls_is_admin(True).
                payload = _jwt.get_unverified_claims(token)
                tenant_id = payload.get("tenant_id") or ""
                user_id = str(payload.get("sub", ""))

                from src.db.tenant_context import (
                    set_db_tenant_id,
                    set_rls_is_admin,
                    set_rls_user_id,
                )

                set_db_tenant_id(tenant_id)
                set_rls_is_admin(False)  # jamais True depuis claims non vérifiés
                set_rls_user_id(user_id)
            except Exception as exc:
                logger.warning(
                    "tenant_context_middleware_parse_error",
                    extra={"error": str(exc)[:200]},
                )
        return await call_next(request)


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

        p = request.url.path
        if p.startswith("/auth") or p.startswith("/api/auth"):
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
        # CI / pytest : Redis actif + milliers de requêtes TestClient → 429 massifs
        # sans bypass (même IP, fenêtre 60s). TESTING=true est posé dans tests/conftest.
        if os.environ.get("TESTING", "false").lower() == "true":
            return await call_next(request)

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
