"""
Tests webhook corpus — secret optionnel, dépôt m12-v2 (mocks).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_BACKEND_PATH = Path(__file__).resolve().parent.parent / "backend.py"
_BACKEND_MODULE = None


def _load_backend_module():
    global _BACKEND_MODULE
    if _BACKEND_MODULE is not None:
        return _BACKEND_MODULE
    spec = importlib.util.spec_from_file_location("backend", _BACKEND_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"backend introuvable : {_BACKEND_PATH}")
    _repo = Path(__file__).resolve().parents[3]
    if str(_repo) not in sys.path:
        sys.path.insert(0, str(_repo))
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("backend", module)
    spec.loader.exec_module(module)
    _BACKEND_MODULE = module
    return module


@pytest.fixture(scope="module", autouse=True)
def _backend_env_module() -> None:
    os.environ.setdefault("PSEUDONYM_SALT", "test-sel-corpus")
    os.environ.setdefault("ALLOW_WEAK_PSEUDONYMIZATION", "1")
    _load_backend_module()
    yield


@pytest.fixture(autouse=True)
def _backend_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "PSEUDONYM_SALT", os.environ.get("PSEUDONYM_SALT", "test-sel-corpus")
    )
    monkeypatch.setenv(
        "ALLOW_WEAK_PSEUDONYMIZATION",
        os.environ.get("ALLOW_WEAK_PSEUDONYMIZATION", "1"),
    )


class TestWebhookSecret:
    def test_rejects_when_secret_configured_and_header_wrong(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_CORPUS_SECRET", "expected")
        from starlette.testclient import TestClient

        backend = _load_backend_module()
        client = TestClient(backend.app)
        r = client.post(
            "/webhook",
            json={"action": "ANNOTATION_UPDATED"},
            headers={"X-Webhook-Secret": "wrong"},
        )
        assert r.status_code == 401
        assert r.json().get("reason") == "unauthorized"

    def test_accepts_matching_secret(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_CORPUS_SECRET", "expected")
        from starlette.testclient import TestClient

        backend = _load_backend_module()
        client = TestClient(backend.app)
        r = client.post(
            "/webhook",
            json={"action": "ANNOTATION_UPDATED"},
            headers={"X-Webhook-Secret": "expected"},
        )
        assert r.status_code == 200


class TestCorpusWebhookProcessing:
    def test_skipped_when_disabled(self, monkeypatch):
        monkeypatch.setenv("CORPUS_WEBHOOK_ENABLED", "0")
        monkeypatch.setenv("LABEL_STUDIO_URL", "https://ls.example")
        monkeypatch.setenv("LABEL_STUDIO_API_KEY", "k")

        _ab = Path(__file__).resolve().parent.parent
        if str(_ab) not in sys.path:
            sys.path.insert(0, str(_ab))
        import corpus_webhook

        called: list[bool] = []

        class Sink:
            def append_line(self, line):
                called.append(True)

        corpus_webhook.process_label_studio_webhook_for_corpus(
            {"action": "ANNOTATION_UPDATED"},
            sink=Sink(),
        )
        assert called == []

    def test_appends_when_enabled_mocked_line(self, monkeypatch):
        monkeypatch.setenv("CORPUS_WEBHOOK_ENABLED", "1")
        monkeypatch.setenv("LABEL_STUDIO_URL", "https://ls.example")
        monkeypatch.setenv("LABEL_STUDIO_API_KEY", "k")

        _ab = Path(__file__).resolve().parent.parent
        if str(_ab) not in sys.path:
            sys.path.insert(0, str(_ab))
        import corpus_webhook

        fake_line = {
            "content_hash": "deadbeefdeadbeef",
            "export_ok": True,
            "ls_meta": {"task_id": 1, "annotation_id": 2, "project_id": 3},
        }

        captured: list[dict] = []

        class Sink:
            def append_line(self, line):
                captured.append(line)

        with patch.object(
            corpus_webhook,
            "ls_annotation_to_m12_v2_line",
            return_value=fake_line,
        ):
            with patch.object(
                corpus_webhook,
                "resolve_task_and_annotation",
                return_value=({"id": 1, "data": {}}, {"id": 2, "result": []}),
            ):
                corpus_webhook.process_label_studio_webhook_for_corpus(
                    {"action": "ANNOTATION_UPDATED", "project": {"id": 3}},
                    sink=Sink(),
                )

        assert len(captured) == 1
        assert captured[0]["content_hash"] == "deadbeefdeadbeef"

    def test_appends_with_ls_url_fallback_not_label_studio_prefix(self, monkeypatch):
        """LS_URL / LS_API_KEY sans LABEL_STUDIO_* — même comportement."""
        monkeypatch.setenv("CORPUS_WEBHOOK_ENABLED", "1")
        monkeypatch.delenv("LABEL_STUDIO_URL", raising=False)
        monkeypatch.delenv("LABEL_STUDIO_API_KEY", raising=False)
        monkeypatch.setenv("LS_URL", "https://ls.example")
        monkeypatch.setenv("LS_API_KEY", "k")

        _ab = Path(__file__).resolve().parent.parent
        if str(_ab) not in sys.path:
            sys.path.insert(0, str(_ab))
        import corpus_webhook

        fake_line = {
            "content_hash": "deadbeefdeadbeef",
            "export_ok": True,
            "ls_meta": {"task_id": 1, "annotation_id": 2, "project_id": 3},
        }

        captured: list[dict] = []

        class Sink:
            def append_line(self, line):
                captured.append(line)

        with patch.object(
            corpus_webhook,
            "ls_annotation_to_m12_v2_line",
            return_value=fake_line,
        ):
            with patch.object(
                corpus_webhook,
                "resolve_task_and_annotation",
                return_value=({"id": 1, "data": {}}, {"id": 2, "result": []}),
            ):
                corpus_webhook.process_label_studio_webhook_for_corpus(
                    {"action": "ANNOTATION_UPDATED", "project": {"id": 3}},
                    sink=Sink(),
                )

        assert len(captured) == 1


class TestObjectKey:
    def test_object_key_stable(self):
        _ab = Path(__file__).resolve().parent.parent
        if str(_ab) not in sys.path:
            sys.path.insert(0, str(_ab))
        from corpus_sink import object_key_for_line

        key = object_key_for_line(
            {
                "content_hash": "abc",
                "ls_meta": {
                    "task_id": 10,
                    "annotation_id": 20,
                    "project_id": 30,
                },
            },
            prefix="m12-v2",
        )
        assert key == "m12-v2/30/10_20_abc.json"
