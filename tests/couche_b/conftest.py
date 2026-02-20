"""Pytest fixtures for Couche B tests — PostgreSQL with transaction rollback (ADR-0003: no ORM)."""

from __future__ import annotations

import pytest


@pytest.fixture
def db_cursor(db_transaction):
    """Expose root db_transaction cursor for resolvers tests (same transaction, rollback on teardown)."""
    return db_transaction
