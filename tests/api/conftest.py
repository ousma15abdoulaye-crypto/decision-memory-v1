"""Fixtures pour tests API criteria — M-CRITERIA-TYPING."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from src.api.main import app


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """TestClient FastAPI pour tests API criteria."""
    return TestClient(app)


@pytest.fixture
def crit_auth(test_client: TestClient) -> dict:
    """JWT admin + tenant_id issu du token (aligné user_tenants / migration 051)."""
    r = test_client.post(
        "/auth/token", data={"username": "admin", "password": "admin123"}
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    tid = jose_jwt.get_unverified_claims(token).get("tenant_id") or "tenant-1"
    return {"headers": {"Authorization": f"Bearer {token}"}, "tid": tid}
