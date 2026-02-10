"""Test Couche B catalog search and market intelligence."""
import pytest


@pytest.mark.asyncio
async def test_catalog_vendor_search(client, admin_headers):
    """Create a vendor via market-signal then search."""
    await client.post(
        "/api/market-signals",
        json={"item_name": "cement", "vendor_name": "TestVendor", "unit_price": 500},
        headers=admin_headers,
    )
    resp = await client.get("/api/catalog/vendors/search?q=TestVendor", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(v["canonical_name"] == "TestVendor" for v in data)


@pytest.mark.asyncio
async def test_catalog_item_search(client, admin_headers):
    await client.post(
        "/api/market-signals",
        json={"item_name": "cement_bags", "vendor_name": "V1", "unit_price": 200},
        headers=admin_headers,
    )
    resp = await client.get("/api/catalog/items/search?q=cement", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_market_stats(client, admin_headers):
    """Insert multiple signals and check stats."""
    for price in [100, 200, 300]:
        await client.post(
            "/api/market-signals",
            json={"item_name": "steel", "vendor_name": "V2", "unit_price": price},
            headers=admin_headers,
        )
    # Get item_id
    items = await client.get("/api/catalog/items/search?q=steel", headers=admin_headers)
    item_id = items.json()[0]["id"]

    resp = await client.get(f"/api/market-intelligence/stats?item_id={item_id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert data["min"] == 100
    assert data["max"] == 300
    assert data["avg"] == 200.0
