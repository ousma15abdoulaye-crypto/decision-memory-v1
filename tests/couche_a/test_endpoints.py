from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.couche_a import models
from src.couche_a.routers import router


def _build_client(tmp_path: Path, monkeypatch) -> TestClient:
    db_path = tmp_path / "couche_a.sqlite3"
    monkeypatch.setenv("COUCHE_A_DB_PATH", str(db_path))
    monkeypatch.delenv("COUCHE_A_DB_URL", raising=False)
    models.reset_engine()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_depot_dashboard_and_export(tmp_path: Path, monkeypatch) -> None:
    client = _build_client(tmp_path, monkeypatch)
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
