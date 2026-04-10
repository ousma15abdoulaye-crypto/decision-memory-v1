"""Middleware tenant context DMS V5.2 — canonique.

Remplace src/couche_a/auth/middleware.py::TenantContextMiddleware
comme référence pour les nouvelles routes (Couche B / V5.x).
L'ancienne classe reste fonctionnelle pour la Couche A existante.

FLUX DE POSE DES VARIABLES DE SESSION POSTGRESQL :
  1. Ce middleware (ASGI) lit le JWT → extrait tenant_id + user_id
  2. Il appelle set_db_tenant_id() et set_rls_user_id() — Python contextvars
  3. Chaque connexion DB (src/db/core.py::get_connection) lit les contextvars
     et pose les GUC PostgreSQL :
       SET app.tenant_id     = '{tenant_id}'
       SET app.current_tenant= '{tenant_id}'
       SET app.is_admin      = 'true'   (si admin)
       SET app.user_id       = '{user_id}'
       SET app.current_user  = '{user_id}'   ← P1.2 : ajout pour trigger

SÉCURITÉ :
  - get_unverified_claims() : NE vérifie PAS la signature JWT.
  - app.is_admin forcé à False ici (jamais promu depuis claims non vérifiés).
  - La promotion is_admin = True est réservée à get_current_user() (signature vérifiée).
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Pose tenant_id + user_id dans les contextvars de la requête.

    Le DB layer (src/db/core.py::get_connection) lit ces contextvars
    et les traduit en GUC PostgreSQL (SET app.tenant_id / app.current_user).

    Comportement :
      - Pas de Bearer     → no-op (requête anonyme ou health check).
      - Bearer présent    → pose tenant_id + user_id, is_admin=False.
      - Lecture JWT échoue → no-op + log WARNING, jamais bloquer.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return await call_next(request)

        token = auth[7:]
        try:
            from jose import jwt as _jwt

            payload = _jwt.get_unverified_claims(token)
            tenant_id = payload.get("tenant_id") or ""
            user_id = str(payload.get("sub", ""))

            from src.db.tenant_context import (
                set_db_tenant_id,
                set_rls_is_admin,
                set_rls_user_id,
            )

            set_db_tenant_id(tenant_id)
            # Jamais True depuis claims non vérifiés — SÉCURITÉ
            set_rls_is_admin(False)
            # user_id est posé ici → src/db/core.py::get_connection()
            # le convertira en SET app.user_id + SET app.current_user (P1.2)
            if user_id:
                set_rls_user_id(user_id)

        except Exception as exc:
            logger.warning(
                "tenant_context_middleware_parse_error",
                extra={"error": str(exc)[:200]},
            )

        return await call_next(request)
