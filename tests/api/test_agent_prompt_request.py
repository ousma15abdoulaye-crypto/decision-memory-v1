"""Validation du corps POST /api/agent/prompt (évite 422 « Field required » côté clients mal branchés)."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from src.api.routers.agent import AgentPromptRequest


def test_strips_whitespace_on_query():
    m = AgentPromptRequest.model_validate({"query": "  hello  "})
    assert m.query == "hello"


def test_accepts_message_alias():
    m = AgentPromptRequest.model_validate({"message": "hi"})
    assert m.query == "hi"


def test_accepts_prompt_alias():
    m = AgentPromptRequest.model_validate({"prompt": "ok"})
    assert m.query == "ok"


def test_accepts_workspace_id_camel_case():
    wid = "550e8400-e29b-41d4-a716-446655440000"
    m = AgentPromptRequest.model_validate({"query": "x", "workspaceId": wid})
    assert m.workspace_id == UUID(wid)


def test_rejects_empty_query():
    with pytest.raises(ValidationError):
        AgentPromptRequest.model_validate({"query": ""})


def test_rejects_missing_text_field():
    with pytest.raises(ValidationError):
        AgentPromptRequest.model_validate(
            {"workspace_id": "550e8400-e29b-41d4-a716-446655440000"}
        )
