"""Test authentication and authorization."""
import pytest


@pytest.mark.asyncio
async def test_login_returns_token(client):
    resp = await client.post("/api/auth/login", json={"username": "testuser", "role": "buyer"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_role(client):
    resp = await client.post("/api/auth/login", json={"username": "testuser", "role": "hacker"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client):
    resp = await client.get("/api/dashboard")
    assert resp.status_code == 403 or resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_token(client, admin_headers):
    resp = await client.get("/api/dashboard", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_only_rejects_buyer(client, buyer_headers):
    resp = await client.post(
        "/api/market-signals",
        json={"item_name": "cement", "vendor_name": "ACorp", "unit_price": 100},
        headers=buyer_headers,
    )
    assert resp.status_code == 403
