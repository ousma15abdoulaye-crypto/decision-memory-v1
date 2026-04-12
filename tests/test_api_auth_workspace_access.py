"""Couverture PR auth workspace : POST /api/auth/login et WorkspaceAccessService."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from jose import jwt

from main import app
from src.services.workspace_access_service import (
    WORKSPACE_PERMISSIONS,
    WorkspaceAccessService,
    WorkspaceRole,
)

client = TestClient(app)


def test_api_auth_login_success():
    """POST /api/auth/login — 200, tokens, user, tenant_id UUID."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert "refresh_token" in data
    u = data["user"]
    assert u["username"] == "admin"
    assert u["role"] == "admin"
    assert "tenant_id" in u
    uuid.UUID(u["tenant_id"])


def test_api_auth_login_with_email():
    """Login /api/auth/login par email admin principal (seed / migration 098)."""
    response = client.post(
        "/api/auth/login",
        json={"email": "ousma15abdoulaye@gmail.com", "password": "admin123"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "admin"


def test_api_auth_login_accepts_username_key():
    """JSON avec clé ``username`` (style OAuth2) → 200."""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "admin"


def test_api_auth_login_form_urlencoded():
    """Corps application/x-www-form-urlencoded → 200."""
    response = client.post(
        "/api/auth/login",
        data={"email": "admin", "password": "admin123"},
    )
    assert response.status_code == 200


def test_api_auth_login_wrong_password():
    """POST /api/auth/login — mauvais mot de passe → 401."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Identifiant ou mot de passe incorrect"


def test_api_auth_login_unsupported_content_type():
    """Content-Type non supporté (ex. text/plain) → 415."""
    response = client.post(
        "/api/auth/login",
        content='{"email":"admin","password":"admin123"}',
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 415
    assert "application/json" in response.json()["detail"]


def test_api_auth_login_jwt_role_admin():
    """JWT émis par /api/auth/login : rôle mappé V4.1.0 (admin)."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    payload = jwt.get_unverified_claims(token)
    assert payload.get("role") == "admin"
    assert payload.get("type") == "access"
    assert "tenant_id" in payload
    uuid.UUID(str(payload["tenant_id"]))


def test_workspace_role_matrix_has_observer_read():
    assert "matrix.read" in WORKSPACE_PERMISSIONS[WorkspaceRole.OBSERVER]


def _mock_db_context(mock_gc: MagicMock) -> None:
    ctx = MagicMock()
    ctx.__enter__.return_value = MagicMock()
    ctx.__exit__.return_value = None
    mock_gc.return_value = ctx


@patch("src.services.workspace_access_service.db_fetchall")
@patch("src.services.workspace_access_service.get_connection")
def test_workspace_check_permission_allows(mock_gc, mock_fetch):
    _mock_db_context(mock_gc)
    mock_fetch.return_value = [{"role": "committee_member", "coi_declared": False}]
    ws, tid = str(uuid.uuid4()), str(uuid.uuid4())
    assert WorkspaceAccessService.check_permission(ws, 1, "matrix.read", tid) is True


@patch("src.services.workspace_access_service.db_fetchall")
@patch("src.services.workspace_access_service.get_connection")
def test_workspace_unknown_role_skipped(mock_gc, mock_fetch):
    _mock_db_context(mock_gc)
    mock_fetch.return_value = [{"role": "unknown_xyz", "coi_declared": False}]
    ws, tid = str(uuid.uuid4()), str(uuid.uuid4())
    assert WorkspaceAccessService.check_permission(ws, 1, "matrix.read", tid) is False


@patch("src.services.workspace_access_service.db_fetchall")
@patch("src.services.workspace_access_service.get_connection")
def test_workspace_coi_blocks_deliberation_validate(mock_gc, mock_fetch):
    _mock_db_context(mock_gc)
    mock_fetch.return_value = [{"role": "committee_chair", "coi_declared": True}]
    ws, tid = str(uuid.uuid4()), str(uuid.uuid4())
    assert (
        WorkspaceAccessService.check_permission(ws, 1, "deliberation.validate", tid)
        is False
    )


def test_workspace_invalid_tenant_short_circuits():
    with patch("src.services.workspace_access_service.db_fetchall") as mock_fetch:
        assert (
            WorkspaceAccessService.check_permission(
                str(uuid.uuid4()),
                1,
                "matrix.read",
                "tenant-999",
            )
            is False
        )
        mock_fetch.assert_not_called()
