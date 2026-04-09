"""get_current_user : pas de psycopg.connect si Bearer absent (V5.1 fermeture écarts)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import src.couche_a.auth.dependencies as auth_dependencies
from main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_members_route_no_bearer_does_not_open_db_connection(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    connect_calls: list[object] = []

    def _no_connect(*_a, **_kw):
        connect_calls.append(True)
        raise AssertionError("psycopg.connect must not run without Bearer token")

    monkeypatch.setattr(auth_dependencies.psycopg, "connect", _no_connect)

    r = client.get(
        "/api/workspaces/00000000-0000-0000-0000-000000000001/members",
    )
    assert r.status_code == 401, r.text
    assert connect_calls == []
