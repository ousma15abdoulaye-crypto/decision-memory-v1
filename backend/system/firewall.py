"""Firewall enforcement – restricts cross-layer access and validates payloads.

Layer rules:
  - Couche A routes may call Couche B *only* via the outbox (market-signal emission).
  - Couche B NEVER calls Couche A directly.
  - The POST /api/market-signals endpoint is reserved for admin / internal service.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

__all__ = [
    "ALLOWED_SIGNAL_FIELDS",
    "validate_market_signal_payload",
    "FirewallMiddleware",
]

# ---- Signal payload whitelist -----------------------------------------------

ALLOWED_SIGNAL_FIELDS: set[str] = {
    "item_name",
    "vendor_name",
    "geo_name",
    "unit_code",
    "unit_price",
    "currency",
    "quantity",
    "signal_date",
    "source",
    "case_reference",
}


def validate_market_signal_payload(data: dict) -> dict:
    """Reject any payload that contains fields outside the whitelist."""
    extra = set(data.keys()) - ALLOWED_SIGNAL_FIELDS
    if extra:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Forbidden fields in market signal payload: {extra}",
        )
    return data


# ---- Cross-layer firewall middleware ----------------------------------------

# Routes that Couche-B must NOT call on Couche-A
_BLOCKED_B_TO_A = {"/api/depot", "/api/export-cba", "/api/pv/opening", "/api/pv/analysis"}

# Header used by internal service-to-service calls to declare origin layer
_ORIGIN_HEADER = "X-DMS-Origin-Layer"


class FirewallMiddleware(BaseHTTPMiddleware):
    """Block cross-layer calls that violate the architecture contract."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get(_ORIGIN_HEADER, "").lower()
        path = request.url.path

        if origin == "couche_b" and path in _BLOCKED_B_TO_A:
            return Response(
                content='{"detail":"Firewall: Couche B cannot call Couche A routes"}',
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json",
            )

        return await call_next(request)
