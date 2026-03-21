"""401 sur routes extractions sans Bearer (couche get_current_user)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(app)


def test_extract_without_token_401(api_client: TestClient) -> None:
    r = api_client.post("/api/extractions/documents/doc-x/extract")
    assert r.status_code == 401


def test_job_status_without_token_401(api_client: TestClient) -> None:
    r = api_client.get("/api/extractions/jobs/job-x/status")
    assert r.status_code == 401


def test_get_extraction_result_without_token_401(api_client: TestClient) -> None:
    r = api_client.get("/api/extractions/documents/doc-x")
    assert r.status_code == 401
