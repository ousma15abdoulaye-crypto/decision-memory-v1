"""POST /api/agent/prompt — validation HTTP du corps JSON (évite 422 « Field required »)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from src.couche_a.auth.dependencies import UserClaims, get_current_user


@pytest.fixture
def _agent_user_override():
    app.dependency_overrides[get_current_user] = lambda: UserClaims(
        user_id="100",
        role="admin",
        jti="test-jti-agent-prompt",
        tenant_id=str(uuid4()),
    )
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_agent_prompt_empty_body_422_missing_query(_agent_user_override) -> None:
    """Corps {} → 422 Pydantic sur ``query`` (repro « Field required »).

    Un corps avec ``query`` / ``message`` / ``prompt`` est couvert par
    ``tests/api/test_agent_prompt_request.py`` ; le chemin complet handler + DB +
    Langfuse n'est pas exécuté ici.
    """
    client = TestClient(app)
    r = client.post("/api/agent/prompt", json={})
    assert r.status_code == 422
    detail = r.json().get("detail")
    assert isinstance(detail, list)
    assert any(
        isinstance(x, dict)
        and "msg" in x
        and "required" in str(x.get("msg", "")).lower()
        for x in detail
    )
