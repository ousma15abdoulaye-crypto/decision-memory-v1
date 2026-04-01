"""Smoke minimal sur main:app — préfixes critiques montés en prod (évite régression d'oubli de router)."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.usefixtures("_env_main_parity")


@pytest.fixture(scope="module", autouse=True)
def _env_main_parity() -> None:
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+psycopg://dms_user:dms_local@localhost:5432/dms_dev",
    )
    os.environ.setdefault("JWT_SECRET", "test-smoke-main-parity-local")
    os.environ.setdefault("ENV", "dev")
    os.environ.setdefault("TESTING", "true")


def test_main_openapi_includes_criteria_and_geo() -> None:
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as client:
        r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths") or {}
    path_keys = list(paths.keys())
    assert any(
        "criteria" in p for p in path_keys
    ), "OpenAPI doit exposer au moins un chemin criteria (router Couche A)"
    assert any(
        "/geo" in p for p in path_keys
    ), "OpenAPI doit exposer le préfixe /geo si le module geo est importable"
