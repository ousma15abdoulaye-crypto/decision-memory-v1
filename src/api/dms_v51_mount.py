"""Montage canonique V5.1 — workspace HTTP + WebSocket (Canon O0, O2, O4, O11, O12).

Un seul appel depuis chaque entrypoint FastAPI (``main.py``, ``src.api.main``)
pour limiter la dérive documentée en ADR dual entrypoints.
"""

from __future__ import annotations

from fastapi import FastAPI

from src.api.workspace_stack import (
    mount_v51_workspace_routes,
    mount_workspace_websockets,
)


def mount_v51_workspace_http_and_ws(app: FastAPI) -> None:
    """Inclut routers dashboard / agent / MQL / membres et routes WebSocket O2."""
    mount_v51_workspace_routes(app)
    mount_workspace_websockets(app)
