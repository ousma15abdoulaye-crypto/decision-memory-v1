"""Smoke backend MN-ENV-SETUP-T14-GEN13 — aucune logique métier."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.usefixtures("_env_smoke")


@pytest.fixture(scope="module", autouse=True)
def _env_smoke() -> None:
    """Charge les variables minimales avant import de l'application."""
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+psycopg://dms_user:dms_local@localhost:5432/dms_dev",
    )
    os.environ.setdefault("JWT_SECRET", "test-smoke-healthcheck-local")
    os.environ.setdefault("ENV", "dev")
    os.environ.setdefault("TESTING", "true")


def test_healthcheck() -> None:
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
