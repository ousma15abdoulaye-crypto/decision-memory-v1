"""Smoke minimal sur main:app — criteria obligatoire ; /geo si le paquet geo est importable.

``DATABASE_URL`` doit être défini avant la collection (voir ``tests/conftest.py``).
"""

from __future__ import annotations

import importlib.util

from fastapi.testclient import TestClient


def _geo_package_available() -> bool:
    return importlib.util.find_spec("src.geo.router") is not None


def test_main_openapi_includes_criteria_and_geo_when_geo_available() -> None:
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
        "/api/m14" in p for p in path_keys
    ), "OpenAPI doit exposer au moins un chemin /api/m14 (M14 Evaluation Engine)"
    if _geo_package_available():
        assert any("/geo" in p for p in path_keys), (
            "Module src.geo présent mais aucun chemin /geo dans OpenAPI — "
            "oubli de montage dans main.py ?"
        )


def test_src_api_main_openapi_includes_m14() -> None:
    """Parité : src.api.main:app expose aussi /api/m14."""
    from src.api.main import app

    with TestClient(app) as client:
        r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths") or {}
    path_keys = list(paths.keys())
    assert any(
        "/api/m14" in p for p in path_keys
    ), "src.api.main:app doit monter le router M14 (/api/m14)"
