"""Test firewall enforcement."""
import pytest


@pytest.mark.asyncio
async def test_market_signal_forbidden_field(client, admin_headers):
    """Extra fields in market signal payload should be rejected."""
    resp = await client.post(
        "/api/market-signals",
        json={
            "item_name": "cement",
            "vendor_name": "ACorp",
            "unit_price": 100,
            "forbidden_field": "hack",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_market_signal_valid(client, admin_headers):
    """Valid market signal should be accepted."""
    resp = await client.post(
        "/api/market-signals",
        json={"item_name": "cement", "vendor_name": "ACorp", "unit_price": 100},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert "signal_id" in resp.json()


@pytest.mark.asyncio
async def test_firewall_b_to_a_blocked(client, admin_headers):
    """Cross-layer call from Couche B to Couche A should be blocked."""
    resp = await client.post(
        "/api/depot",
        headers={**admin_headers, "X-DMS-Origin-Layer": "couche_b"},
        data={"case_id": "C1", "lot_id": "L1"},
    )
    assert resp.status_code == 403
