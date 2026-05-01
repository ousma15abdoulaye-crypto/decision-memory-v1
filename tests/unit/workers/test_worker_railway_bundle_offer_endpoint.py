from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient


class FakeCursor:
    def __init__(self, row):
        self.row = row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def execute(self, *_args, **_kwargs) -> None:
        return None

    async def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row):
        self.row = row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def cursor(self):
        return FakeCursor(self.row)


class FakePool:
    def __init__(self):
        self.enqueued: list[tuple] = []

    async def enqueue_job(self, *args, **kwargs):
        self.enqueued.append((args, kwargs))
        return SimpleNamespace(job_id="job-1")

    async def close(self) -> None:
        return None


def _load_worker_module(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("WORKER_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("ARQ_REDIS_URL", "redis://localhost:6379")
    module_name = "worker_railway_main_test"
    sys.modules.pop(module_name, None)
    path = (
        Path(__file__).resolve().parents[3] / "services" / "worker-railway" / "main.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_bundle_offer_extract_endpoint_requires_bearer(monkeypatch) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)

    response = client.post(
        "/arq/enqueue/bundle-offer-extract",
        json={"workspace_id": str(uuid.uuid4()), "bundle_id": str(uuid.uuid4())},
    )

    assert response.status_code == 401


def test_bundle_offer_extract_endpoint_enqueues_scopable_task(monkeypatch) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)
    workspace_id = uuid.uuid4()
    bundle_id = uuid.uuid4()
    row = (
        str(bundle_id),
        str(workspace_id),
        "scorable",
        1,
        1,
        1,
        1,
        0,
    )
    pool = FakePool()

    async def fake_connect(*_args, **_kwargs):
        return FakeConnection(row)

    async def fake_create_pool(*_args, **_kwargs):
        return pool

    with (
        patch.object(mod.psycopg.AsyncConnection, "connect", fake_connect),
        patch.object(mod, "create_pool", fake_create_pool),
    ):
        response = client.post(
            "/arq/enqueue/bundle-offer-extract",
            headers={"Authorization": "Bearer secret-token"},
            json={"workspace_id": str(workspace_id), "bundle_id": str(bundle_id)},
        )

    assert response.status_code == 202
    assert response.json()["function"] == "extract_supplier_bundle_offer_task"
    assert pool.enqueued[0][0][0] == "extract_supplier_bundle_offer_task"
    assert pool.enqueued[0][1] == {
        "workspace_id": str(workspace_id),
        "bundle_id": str(bundle_id),
        "force": False,
    }


def test_bundle_offer_extract_endpoint_rejects_invalid_payload(monkeypatch) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)

    response = client.post(
        "/arq/enqueue/bundle-offer-extract",
        headers={"Authorization": "Bearer secret-token"},
        json={"workspace_id": "not-a-uuid", "bundle_id": str(uuid.uuid4())},
    )

    assert response.status_code == 422
