"""M-CTO-V53-F — route GET /api/workspaces/{id}/event-timeline (smoke auth)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.workspaces import router


def test_timeline_requires_bearer():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/api/workspaces/ws-1/event-timeline")
    assert r.status_code == 401
