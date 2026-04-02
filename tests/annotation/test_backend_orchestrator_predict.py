"""M12 Phase 3 — /predict branché sur AnnotationOrchestrator (sans appel Mistral réel)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from src.annotation.orchestrator import (
    AnnotationOrchestrator,
    AnnotationPipelineState,
    PipelineRunRecord,
)

BACKEND_PATH = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "annotation-backend"
    / "backend.py"
)

_LONG_TEXT = (
    "PROPOSITION TECHNIQUE\n" + "word " * 80
).strip()  # > MIN_PREDICT & MIN_LLM


def _load_backend(name: str):
    _repo = Path(__file__).resolve().parents[2]
    if str(_repo) not in sys.path:
        sys.path.insert(0, str(_repo))
    spec = importlib.util.spec_from_file_location(name, BACKEND_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"backend load fail {BACKEND_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    be_root = str(BACKEND_PATH.parent)
    spec.loader.exec_module(mod)
    while len(sys.path) > 1 and sys.path[0] == be_root and sys.path[1] == be_root:
        sys.path.pop(0)
    return mod


@pytest.fixture(autouse=True)
def _orch_predict_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PSEUDONYM_SALT", "test-salt-orch-predict")
    monkeypatch.setenv("ALLOW_WEAK_PSEUDONYMIZATION", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "fake-key")


def test_health_includes_orchestrator_flags(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANNOTATION_USE_PASS_ORCHESTRATOR", "1")
    monkeypatch.setenv("ANNOTATION_USE_M12_SUBPASSES", "0")
    mod = _load_backend("ab_orch_health_1")
    payload = mod._health_payload()
    assert payload["pass_orchestrator_enabled"] is True
    assert payload["m12_subpasses_enabled"] is False
    assert "orchestrator_runs_dir_hint" in payload


def test_predict_delegates_to_mistral_when_orchestrator_off(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("ANNOTATION_USE_PASS_ORCHESTRATOR", raising=False)
    mod = _load_backend("ab_orch_off")
    mod.client = MagicMock()
    mod._call_mistral = AsyncMock(return_value=dict(mod.FALLBACK_RESPONSE))
    client = TestClient(mod.app)
    body = {"document_id": "d1", "tasks": [{"id": 1, "data": {"text": _LONG_TEXT}}]}
    r = client.post("/predict", json=body)
    assert r.status_code == 200
    mod._call_mistral.assert_awaited_once()
    sent = mod._call_mistral.await_args[0][0]
    assert "PROPOSITION TECHNIQUE" in sent and len(sent) >= 200


def test_predict_skips_mistral_on_dead_letter(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    monkeypatch.setenv("ANNOTATION_USE_PASS_ORCHESTRATOR", "1")
    monkeypatch.setenv("ANNOTATION_PIPELINE_RUNS_DIR", str(tmp_path))

    def _fake_run(
        self,
        raw_text: str,
        *,
        document_id: str,
        run_id,
        file_metadata=None,
        filename=None,
        case_documents_1a=None,
        case_id=None,
    ):
        rec = PipelineRunRecord(
            run_id=str(run_id),
            document_id=document_id,
            state=AnnotationPipelineState.DEAD_LETTER.value,
            pass_outputs={},
        )
        return rec, AnnotationPipelineState.DEAD_LETTER

    monkeypatch.setattr(AnnotationOrchestrator, "run_passes_0_to_1", _fake_run)

    mod = _load_backend("ab_orch_dead")
    mod.client = MagicMock()
    mod._call_mistral = AsyncMock(return_value=dict(mod.FALLBACK_RESPONSE))
    client = TestClient(mod.app)
    body = {"document_id": "d1", "tasks": [{"id": 2, "data": {"text": _LONG_TEXT}}]}
    r = client.post("/predict", json=body)
    assert r.status_code == 200
    mod._call_mistral.assert_not_awaited()
    inner = json.loads(r.json()["results"][0]["result"][0]["value"]["text"][0])
    assert "orchestrator_dead_letter" in inner.get("_meta", {}).get("error_reason", "")


def test_predict_uses_normalized_text_when_llm_pending(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    monkeypatch.setenv("ANNOTATION_USE_PASS_ORCHESTRATOR", "1")
    monkeypatch.setenv("ANNOTATION_PIPELINE_RUNS_DIR", str(tmp_path))
    normalized = "NORMALIZED_BODY " * 30

    def _fake_run(
        self,
        raw_text: str,
        *,
        document_id: str,
        run_id,
        file_metadata=None,
        filename=None,
        case_documents_1a=None,
        case_id=None,
    ):
        rec = PipelineRunRecord(
            run_id=str(run_id),
            document_id=document_id,
            state=AnnotationPipelineState.LLM_PREANNOTATION_PENDING.value,
            pass_outputs={
                "pass_0_ingestion": {
                    "output_data": {"normalized_text": normalized},
                },
            },
        )
        return rec, AnnotationPipelineState.LLM_PREANNOTATION_PENDING

    monkeypatch.setattr(AnnotationOrchestrator, "run_passes_0_to_1", _fake_run)

    mod = _load_backend("ab_orch_llm_pending")
    mod.client = MagicMock()
    captured: dict[str, str] = {}

    async def _capture_mistral(txt, *a, **k):
        captured["text"] = txt
        return dict(mod.FALLBACK_RESPONSE)

    mod._call_mistral = _capture_mistral
    client = TestClient(mod.app)
    body = {"document_id": "d1", "tasks": [{"id": 3, "data": {"text": _LONG_TEXT}}]}
    r = client.post("/predict", json=body)
    assert r.status_code == 200
    assert captured.get("text") == normalized.strip()
