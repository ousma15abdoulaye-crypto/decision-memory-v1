"""Contexte RLS par requête (app.tenant_id / app.is_admin via set_config).

Rempli par get_current_user après validation JWT.
"""

from __future__ import annotations

import contextvars

_db_tenant_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "db_tenant_id", default=None
)
_db_is_admin: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "rls_is_admin", default=False
)


def set_db_tenant_id(tenant_id: str | None) -> None:
    _db_tenant_id.set(tenant_id)


def get_db_tenant_id() -> str | None:
    return _db_tenant_id.get()


def set_rls_is_admin(is_admin: bool) -> None:
    _db_is_admin.set(is_admin)


def get_rls_is_admin() -> bool:
    return _db_is_admin.get()


def get_rls_tenant_id() -> str | None:
    return _db_tenant_id.get()


def reset_rls_request_context() -> None:
    """Réinitialise le contexte (tests / workers)."""
    _db_tenant_id.set(None)
    _db_is_admin.set(False)
