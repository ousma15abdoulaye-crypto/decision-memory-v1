"""F8 — routes M16 sous /api/workspaces/{workspace_id}/m16/."""

from __future__ import annotations

from src.api.main import app


def test_m16_routes_include_workspace_id() -> None:
    for route in app.routes:
        path = getattr(route, "path", "") or ""
        if "m16" not in path:
            continue
        if "{workspace_id}" not in path:
            raise AssertionError(f"M16 route sans workspace_id: {path}")


def test_thread_routes_not_orphan() -> None:
    for route in app.routes:
        path = getattr(route, "path", "") or ""
        if "thread_id" in path and "workspace_id" not in path:
            raise AssertionError(f"Route thread orpheline: {path}")
