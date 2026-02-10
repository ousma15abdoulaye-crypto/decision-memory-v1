"""Shared test fixtures for DMS backend tests."""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Force SQLite for tests — must be set before any backend import
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_dms.db"

# Reset cached settings so the env var takes effect
import backend.system.settings as _settings_mod
_settings_mod._settings = None

from backend.main import app
from backend.system.db import engine, Base, async_session_factory
from backend.system.auth import create_access_token


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test and drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def admin_token():
    return create_access_token({"sub": "test-admin-id", "username": "admin", "role": "admin"})


@pytest.fixture
def buyer_token():
    return create_access_token({"sub": "test-buyer-id", "username": "buyer", "role": "buyer"})


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def buyer_headers(buyer_token):
    return {"Authorization": f"Bearer {buyer_token}"}
