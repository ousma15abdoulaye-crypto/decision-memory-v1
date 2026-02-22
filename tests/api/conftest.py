"""Fixtures pour tests API criteria — M-CRITERIA-TYPING."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """TestClient FastAPI pour tests API criteria."""
    return TestClient(app)
