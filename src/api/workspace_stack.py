"""Montage commun — routes V5.1 workspace (dashboard, agent, MQL, membres, WebSocket).

Évite la dérive entre ``main.py`` (Railway) et ``src.api.main`` (app modulaire).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def mount_v51_workspace_routes(app: FastAPI) -> None:
    """Canon O0 / O4 / O11 / O12 — routers HTTP."""
    from src.api.routers.agent import router as _agent_router
    from src.api.routers.dashboard import router as _dashboard_router
    from src.api.routers.mql import router as _mql_router
    from src.api.routers.workspace_members import router as _workspace_members_router

    app.include_router(_dashboard_router)
    app.include_router(_agent_router)
    app.include_router(_mql_router)
    app.include_router(_workspace_members_router)


def mount_workspace_websockets(app: FastAPI) -> None:
    """Canon O2 — WebSocket événements workspace (chemin historique + alias canon)."""
    try:
        from src.api.ws.workspace_events import workspace_events_ws
    except ModuleNotFoundError as exc:
        logger.warning("[workspace_stack] module WebSocket workspace absent : %s", exc)
        return

    app.add_api_websocket_route(
        "/ws/workspace/{workspace_id}/events",
        workspace_events_ws,
        name="workspace_events_ws",
    )
    app.add_api_websocket_route(
        "/ws/workspace/{workspace_id}",
        workspace_events_ws,
        name="workspace_events_ws_canon_o2",
    )
