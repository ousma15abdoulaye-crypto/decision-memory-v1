"""POST /api/workspaces/{id}/comments sur main:app (Canon O8) — DB requise."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    return TestClient(app)


def _admin_headers(c: TestClient) -> dict[str, str]:
    r = c.post(
        "/api/auth/login",
        json={"email": "admin", "password": "admin123"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_post_comment_requires_auth(client: TestClient) -> None:
    wid = str(uuid.uuid4())
    r = client.post(f"/api/workspaces/{wid}/comments", json={"content": "x"})
    assert r.status_code in (401, 403)


def test_post_workspace_level_comment_admin(client: TestClient) -> None:
    headers = _admin_headers(client)
    ref = f"TST-CMT-{uuid.uuid4().hex[:8]}"
    cr = client.post(
        "/api/workspaces",
        headers=headers,
        json={
            "title": "Comment test workspace",
            "reference_code": ref,
            "process_type": "devis_simple",
        },
    )
    assert cr.status_code == 201, cr.text
    ws_id = cr.json()["workspace_id"]

    r = client.post(
        f"/api/workspaces/{ws_id}/comments",
        headers=headers,
        json={"content": "Commentaire workspace-level", "is_flag": False},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "comment_id" in data
    assert "thread_id" in data
    assert data.get("comment_type") in ("comment", "flag", "question")


def test_post_cell_comment_unknown_cell_404(client: TestClient) -> None:
    headers = _admin_headers(client)
    ref = f"TST-CMT2-{uuid.uuid4().hex[:8]}"
    cr = client.post(
        "/api/workspaces",
        headers=headers,
        json={
            "title": "Comment cell test",
            "reference_code": ref,
            "process_type": "devis_simple",
        },
    )
    assert cr.status_code == 201, cr.text
    ws_id = cr.json()["workspace_id"]

    r = client.post(
        f"/api/workspaces/{ws_id}/comments",
        headers=headers,
        json={
            "content": "n/a",
            "criterion_id": "nonexistent_key",
            "supplier_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 404
