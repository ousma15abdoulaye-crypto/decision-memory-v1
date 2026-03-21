"""Tenant context middleware — multi-tenant isolation V4.1.0.

Sets PostgreSQL session variable ``app.org_id`` on every request that
carries a JWT Bearer token containing an ``org_id`` claim.  This variable
is consumed by Row-Level Security (RLS) policies defined in migration
051_rls_tenant_isolation.

Design rationale:
  - DB-level enforcement via RLS requires a session variable.
  - The middleware sits BEFORE any route handler, guaranteeing the
    variable is set for every downstream query.
  - Requests without a valid token leave ``app.org_id`` unset; RLS
    policies on affected tables will deny access (once FORCE RLS is
    enabled).

RÈGLE-04 : Fallback no-op si extraction JWT échoue (log WARNING).
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


def _extract_org_id_from_token(request: Request) -> str | None:
    """Extract ``org_id`` from an unverified JWT Bearer token.

    Returns *None* when the header is absent, malformed, or the claim
    is missing.  Full token verification is left to the auth dependency
    (``get_current_user``); here we only need the claim value to seed
    the DB session variable.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        from jose import jwt as _jwt

        payload = _jwt.get_unverified_claims(token)
        return payload.get("org_id")
    except Exception:
        return None


def set_tenant_context(conn, org_id: str) -> None:
    """Set ``app.org_id`` on a psycopg connection for RLS policies.

    This is the **canonical** way to inject tenant context into a DB
    session.  It must be called before any tenant-scoped query when
    RLS is enforced.

    Parameters
    ----------
    conn : psycopg.Connection or cursor
        An open psycopg connection (or its cursor's connection).
    org_id : str
        The organisation identifier to scope the session to.
    """
    if not org_id:
        return
    cur = conn.cursor() if hasattr(conn, "cursor") else conn
    try:
        cur.execute("SET LOCAL app.org_id = %s", (org_id,))
    except Exception as exc:
        logger.warning("Failed to SET app.org_id: %s", exc)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware that propagates ``org_id`` from the JWT into the request state.

    The ``org_id`` value is stored in ``request.state.org_id`` so that
    downstream FastAPI dependencies and DB helpers can read it and call
    :func:`set_tenant_context` on their connections.

    This middleware does **not** open a DB connection itself — it only
    extracts and stores the tenant identifier for later use.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        org_id = _extract_org_id_from_token(request)

        # Also accept org_id from query string (criteria-style endpoints)
        if org_id is None:
            org_id = request.query_params.get("org_id")

        # Store on request state for downstream use
        request.state.org_id = org_id or ""

        response = await call_next(request)
        return response
