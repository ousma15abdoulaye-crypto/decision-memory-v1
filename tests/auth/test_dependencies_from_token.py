"""get_current_user_from_token — parité tenant RLS avec HTTP (WebSocket)."""

from __future__ import annotations

import pytest

import src.couche_a.auth.dependencies as auth_dependencies
from src.couche_a.auth.dependencies import get_current_user_from_token
from src.couche_a.auth.jwt_handler import create_access_token
from src.db.tenant_context import (
    get_db_tenant_id,
    get_rls_is_admin,
    get_rls_user_id,
    reset_rls_request_context,
)


def _expected_default_tenant_uuid(db_conn) -> str:
    from src.couche_a.auth.dependencies import _default_tenant_code

    code = _default_tenant_code()
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT id::text FROM tenants WHERE code = %s LIMIT 1",
            (code,),
        )
        row = cur.fetchone()
    assert row and row[0], f"tenant code {code!r} introuvable en base de test"
    return str(row[0]).strip()


def test_get_current_user_from_token_resolves_legacy_tenant_claim(db_conn):
    """JWT ``tenant-<id>`` → même UUID RLS que ``_resolve_tenant_uuid_for_rls`` + contextvars."""
    reset_rls_request_context()
    try:
        token = create_access_token("100", "buyer", tenant_id="tenant-100")
        claims = get_current_user_from_token(token)

        expected_tid = _expected_default_tenant_uuid(db_conn)
        assert claims.tenant_id == expected_tid
        assert claims.user_id == "100"
        assert claims.role == "buyer"
        assert get_db_tenant_id() == expected_tid
        assert get_rls_user_id() == "100"
        assert get_rls_is_admin() is False
    finally:
        reset_rls_request_context()


def test_get_current_user_from_token_admin_sets_rls_admin(db_conn):
    reset_rls_request_context()
    try:
        token = create_access_token("1", "admin", tenant_id="tenant-1")
        claims = get_current_user_from_token(token)

        assert claims.is_superuser is True
        assert get_rls_is_admin() is True
    finally:
        reset_rls_request_context()


def test_get_current_user_from_token_missing_database_url(monkeypatch):
    """DATABASE_URL vide → RuntimeError (distinct de ValueError JWT)."""

    class _Cfg:
        DATABASE_URL = ""

    monkeypatch.setattr(auth_dependencies, "get_settings", lambda: _Cfg())
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        auth_dependencies.get_current_user_from_token("dummy")
