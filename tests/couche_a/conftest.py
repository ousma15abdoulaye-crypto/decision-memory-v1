"""Pytest fixtures for Couche A tests — PostgreSQL ONLY (DATABASE_URL)."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


@pytest.fixture(scope="session")
def db_engine() -> Engine:
    """Provide a PostgreSQL engine for tests. Skips if DATABASE_URL is not set."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL not set – skipping PostgreSQL tests")
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[9:]
    eng = create_engine(db_url)
    yield eng
    eng.dispose()
