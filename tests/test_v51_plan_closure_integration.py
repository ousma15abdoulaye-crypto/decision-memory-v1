"""Fermeture plan V5.1 DevOps-grade — intégration ciblée (DB requise).

- O4 : GET membres sans JWT → 401.
- O12 : POST /api/mql/stream persiste une ligne ``mql_query_log`` (moteur MQL mocké).
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from main import app
from src.mql.engine import MQLResult, MQLSource


@pytest.fixture
def client() -> TestClient:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    return TestClient(app)


def _admin_headers(c: TestClient) -> dict[str, str]:
    r = c.post(
        "/api/auth/login",
        json={"email": "admin", "password": "admin123"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_workspace_members_requires_auth(client: TestClient) -> None:
    wid = str(uuid.uuid4())
    r = client.get(f"/api/workspaces/{wid}/members")
    assert r.status_code == 401


@patch("src.mql.engine.execute_mql_query", new_callable=AsyncMock)
def test_mql_stream_persists_mql_query_log(
    mock_mql: AsyncMock,
    client: TestClient,
    db_conn,
) -> None:
    marker = f"INTEGRATION_MQL_LOG_{uuid.uuid4().hex}"
    mock_mql.return_value = MQLResult(
        template_used="integration_stub",
        rows=[],
        row_count=0,
        sources=[
            MQLSource(
                name="stub",
                source_type="test",
                publisher="test",
                published_date=None,
                is_official=False,
            )
        ],
        confidence=0.8,
        latency_ms=1,
        params_used={},
    )

    headers = _admin_headers(client)
    r = client.post(
        "/api/mql/stream",
        headers=headers,
        json={"query": marker, "workspace_id": None},
    )
    assert r.status_code == 200, r.text

    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, query_text, intent_classified, template_used
              FROM mql_query_log
             WHERE query_text = %s
             ORDER BY created_at DESC
             LIMIT 1
            """,
            (marker,),
        )
        row = cur.fetchone()
    assert row is not None, "mql_query_log doit contenir la requête du test"
    assert row["intent_classified"] == "mql_internal"
    assert row["template_used"] == "integration_stub"
