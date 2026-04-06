from __future__ import annotations

from src.api.routers.documents import router


def test_committee_pv_export_route_exists() -> None:
    paths = [route.path for route in router.routes]
    methods = [route.methods for route in router.routes]
    assert "/api/workspaces/{workspace_id}/committee/pv" in paths
    assert any("GET" in m for m in methods)
