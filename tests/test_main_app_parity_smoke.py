"""Smoke minimal sur main:app — criteria obligatoire ; /geo si le paquet geo est importable.

Inclut les préfixes W1/W3 (workspaces, committee seal, PV) pour parité prod vs
``src.api.main:app`` (voir DD + ADR-DUAL-FASTAPI-ENTRYPOINTS).

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


def test_main_openapi_includes_workspaces_committee_pv_prefixes() -> None:
    """Production expose W1/W3 + exports PV — régression si oubli de montage dans main.py."""
    from main import app

    with TestClient(app) as client:
        r = client.get("/openapi.json")
    assert r.status_code == 200
    path_keys = list((r.json().get("paths") or {}).keys())
    assert any(
        "/api/workspaces" in p for p in path_keys
    ), "OpenAPI doit exposer au moins un chemin /api/workspaces (W1)"
    assert any(
        "/api/dashboard" in p for p in path_keys
    ), "OpenAPI doit exposer /api/dashboard (Canon O0 / V5.1)"
    assert any(
        "/api/agent/prompt" in p for p in path_keys
    ), "OpenAPI doit exposer POST /api/agent/prompt (Canon O11)"
    assert any(
        "comments" in p and "/api/workspaces/" in p for p in path_keys
    ), "OpenAPI doit exposer POST .../comments sous /api/workspaces (O8 CDE)"
    assert any(
        "committee/seal" in p for p in path_keys
    ), "OpenAPI doit exposer committee/seal (W3 scellage)"
    assert any(
        "committee/pv" in p for p in path_keys
    ), "OpenAPI doit exposer committee/pv (exports PV)"
    assert any(
        "/members" in p and "/api/workspaces/" in p for p in path_keys
    ), "OpenAPI doit exposer …/members (Canon O4)"
    assert any(
        p.endswith("/seal") or "/seal}" in p for p in path_keys
    ), "OpenAPI doit exposer POST …/seal (alias Canon O9)"


def test_src_api_main_openapi_includes_v51_workspace_stack() -> None:
    """Parité modulaire : même bundle V5.1 que main.py."""
    from src.api.main import app

    with TestClient(app) as client:
        r = client.get("/openapi.json")
    assert r.status_code == 200
    path_keys = list((r.json().get("paths") or {}).keys())
    assert any("/api/dashboard" in p for p in path_keys)
    assert any("/api/agent/prompt" in p for p in path_keys)
    assert any("/api/mql/stream" in p for p in path_keys)
    assert any("/members" in p and "/api/workspaces/" in p for p in path_keys)
