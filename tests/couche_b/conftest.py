"""Pytest fixtures for Couche B tests — PostgreSQL with transaction rollback."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session


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


@pytest.fixture(scope="function")
def db_session(db_engine) -> Session:
    """Provide a transactional database session for each test.

    Changes are rolled back after each test to ensure isolation.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
