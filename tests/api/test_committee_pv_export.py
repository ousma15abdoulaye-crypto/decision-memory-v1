"""Committee PV exports — route registration + comportements HTTP (mocks)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.routers.documents import router
from src.couche_a.auth.dependencies import UserClaims, get_current_user


def _fake_user() -> UserClaims:
    return UserClaims(
        user_id="42",
        role="admin",
        jti="test-jti-pv",
        tenant_id="00000000-0000-0000-0000-000000000001",
    )


@pytest.fixture()
def _pv_auth_override():
    from src.api.main import app as modular_app

    modular_app.dependency_overrides[get_current_user] = _fake_user
    yield
    modular_app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def modular_client() -> TestClient:
    from src.api.main import app

    return TestClient(app)


def test_committee_pv_export_route_exists() -> None:
    paths = [route.path for route in router.routes]
    methods = [route.methods for route in router.routes]
    assert "/api/workspaces/{workspace_id}/committee/pv" in paths
    assert any("GET" in m for m in methods)


@pytest.mark.usefixtures("_pv_auth_override")
@patch("src.api.routers.documents.require_workspace_access")
@patch("src.api.routers.documents.get_sealed_session")
@patch("src.api.routers.documents.get_connection")
def test_pv_json_409_when_session_not_sealed(
    mock_conn: MagicMock,
    mock_sealed: MagicMock,
    _mock_access: MagicMock,
    modular_client: TestClient,
) -> None:
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_cm
    mock_cm.__exit__.return_value = None
    mock_conn.return_value = mock_cm
    mock_sealed.side_effect = HTTPException(
        status_code=409, detail="Session non scellée."
    )

    r = modular_client.get(
        "/api/workspaces/00000000-0000-0000-0000-0000000000aa/committee/pv?format=json"
    )
    assert r.status_code == 409
    assert "Session" in (r.json().get("detail") or "")


@pytest.mark.usefixtures("_pv_auth_override")
@patch("src.api.routers.documents.require_workspace_access")
@patch("src.api.routers.documents.get_sealed_session")
@patch("src.api.routers.documents.get_connection")
def test_pv_json_500_on_integrity_mismatch(
    mock_conn: MagicMock,
    mock_sealed: MagicMock,
    _mock_access: MagicMock,
    modular_client: TestClient,
) -> None:
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_cm
    mock_cm.__exit__.return_value = None
    mock_conn.return_value = mock_cm
    mock_sealed.side_effect = HTTPException(
        status_code=500,
        detail="Integrity mismatch: le hash recalculé ne correspond pas au hash scellé.",
    )

    r = modular_client.get(
        "/api/workspaces/00000000-0000-0000-0000-0000000000aa/committee/pv?format=json"
    )
    assert r.status_code == 500


@pytest.mark.usefixtures("_pv_auth_override")
@patch("src.api.routers.documents.require_workspace_access")
@patch("src.api.routers.documents.get_sealed_session")
@patch("src.api.routers.documents.get_connection")
def test_pv_json_200_returns_snapshot_payload(
    mock_conn: MagicMock,
    mock_sealed: MagicMock,
    _mock_access: MagicMock,
    modular_client: TestClient,
) -> None:
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_cm
    mock_cm.__exit__.return_value = None
    mock_conn.return_value = mock_cm
    mock_sealed.return_value = {
        "session_id": "11111111-1111-1111-1111-111111111111",
        "sealed_at": "2026-04-06T12:00:00+00:00",
        "seal_hash": "a" * 64,
        "pv_snapshot": {"committee": "test", "rows": []},
    }

    wid = "00000000-0000-0000-0000-0000000000bb"
    r = modular_client.get(f"/api/workspaces/{wid}/committee/pv?format=json")
    assert r.status_code == 200
    data = r.json()
    assert data["workspace_id"] == wid
    assert data["seal_hash"] == "a" * 64
    assert data["pv_snapshot"]["committee"] == "test"


@pytest.mark.usefixtures("_pv_auth_override")
@patch("src.api.routers.documents.require_workspace_access")
@patch("src.api.routers.documents._render_pdf")
@patch("src.api.routers.documents.get_sealed_session")
@patch("src.api.routers.documents.get_connection")
def test_pv_pdf_returns_bytes(
    mock_conn: MagicMock,
    mock_sealed: MagicMock,
    mock_pdf: MagicMock,
    _mock_access: MagicMock,
    modular_client: TestClient,
) -> None:
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_cm
    mock_cm.__exit__.return_value = None
    mock_conn.return_value = mock_cm
    mock_sealed.return_value = {
        "session_id": "22222222-2222-2222-2222-222222222222",
        "sealed_at": "2026-04-06T12:00:00+00:00",
        "seal_hash": "b" * 64,
        "pv_snapshot": {"x": 1},
    }
    mock_pdf.return_value = b"%PDF-1.4 mock"

    r = modular_client.get(
        "/api/workspaces/00000000-0000-0000-0000-0000000000cc/committee/pv?format=pdf"
    )
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")
    assert "pdf" in r.headers.get("content-type", "")


@pytest.mark.usefixtures("_pv_auth_override")
@patch("src.api.routers.documents.require_workspace_access")
@patch("src.api.routers.documents.build_xlsx_export")
@patch("src.api.routers.documents.get_sealed_session")
@patch("src.api.routers.documents.get_connection")
def test_pv_xlsx_returns_workbook(
    mock_conn: MagicMock,
    mock_sealed: MagicMock,
    mock_xlsx: MagicMock,
    _mock_access: MagicMock,
    modular_client: TestClient,
) -> None:
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_cm
    mock_cm.__exit__.return_value = None
    mock_conn.return_value = mock_cm
    mock_sealed.return_value = {
        "session_id": "33333333-3333-3333-3333-333333333333",
        "sealed_at": "2026-04-06T12:00:00+00:00",
        "seal_hash": "c" * 64,
        "pv_snapshot": {"rows": []},
    }
    mock_xlsx.return_value = b"PK\x03\x04mockxlsx"

    r = modular_client.get(
        "/api/workspaces/00000000-0000-0000-0000-0000000000dd/committee/pv?format=xlsx"
    )
    assert r.status_code == 200
    assert r.content.startswith(b"PK")
    assert "spreadsheetml" in r.headers.get("content-type", "")
