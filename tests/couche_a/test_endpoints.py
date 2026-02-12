from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.couche_a.routers import router


@pytest.fixture
def client() -> TestClient:
    """Build a test client. Requires DATABASE_URL (PostgreSQL)."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set – skipping PostgreSQL tests")
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.skip(reason="Endpoint non encore implémenté (Milestone 2B / M5)")
def test_depot_dashboard_and_export(client: TestClient) -> None:
    response = client.post(
        "/api/depot",
        data={"case_id": "CASE1", "lot_id": "LOT1"},
        files={"file": ("dao.txt", b"DAO FOURNISSEUR: ACME\nMontant 1000", "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    offer_id = payload["offer_id"]

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["items"]

    detail = client.get(f"/api/offres/{offer_id}")
    assert detail.status_code == 200
    assert detail.json()["offer"]["id"] == offer_id

    export = client.post("/api/export-cba", json={"offer_id": offer_id})
    assert export.status_code == 200
    assert export.json()["version"] == 1
