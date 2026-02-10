"""
Test Couche B API Routers
Constitution DMS V2.1 §6
"""

import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from src.couche_b.routers import router

# Create test app
app = FastAPI()
app.include_router(router)


@pytest.mark.asyncio
async def test_search_vendors():
    """Test vendor search endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/couche-b/catalog/vendors/search?q=test")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_search_items():
    """Test item search endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/couche-b/catalog/items/search?q=ciment")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_search_units():
    """Test units search endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/couche-b/catalog/units/search?q=kg")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_search_geo():
    """Test geo search endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/couche-b/catalog/geo/search?q=bamako")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_market_survey():
    """Test market survey creation"""
    # This test requires PostgreSQL - skip in SQLite environment
    pytest.skip("Requires PostgreSQL for async operations")


@pytest.mark.asyncio
async def test_get_validation_queue():
    """Test validation queue endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/couche-b/market-survey/validation-queue")
        assert response.status_code == 200
        data = response.json()
        assert 'count' in data
        assert 'signals' in data


@pytest.mark.asyncio
async def test_validate_signal():
    """Test signal validation endpoint"""
    # This test requires PostgreSQL - skip in SQLite environment
    pytest.skip("Requires PostgreSQL for async operations")


@pytest.mark.asyncio
async def test_search_market_intelligence():
    """Test market intelligence search"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/couche-b/market-intelligence/search")
        assert response.status_code == 200
        data = response.json()
        assert 'count' in data
        assert 'signals' in data


@pytest.mark.asyncio
async def test_get_market_stats():
    """Test market statistics endpoint"""
    # This test requires a valid item_id - skip for basic test
    pytest.skip("Requires seeded data for testing")


# Additional sync tests for validation

def test_router_prefix():
    """Test router has correct prefix"""
    assert router.prefix == "/api/couche-b"


def test_router_tags():
    """Test router has correct tags"""
    assert "Couche B - Market Intelligence" in router.tags
