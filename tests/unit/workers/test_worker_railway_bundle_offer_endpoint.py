from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def execute(self, *_args, **_kwargs) -> None:
        return None

    async def fetchone(self):
        return self.row

    async def fetchall(self):
        return self.rows


class FakeCursorContext:
    def __init__(self, cursor):
        self.cursor = cursor

    async def __aenter__(self):
        return self.cursor

    async def __aexit__(self, *_args):
        return False


class FakeConnection:
    def __init__(self, row=None, rows=None, cursors=None):
        self.row = row
        self.rows = rows or []
        self.cursors = list(cursors or [])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def cursor(self):
        if self.cursors:
            return FakeCursorContext(self.cursors.pop(0))
        return FakeCursorContext(FakeCursor(self.row))


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


def test_m4c_snapshot_endpoint_requires_bearer(monkeypatch) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)

    response = client.get(
        "/diagnostics/v1/workspaces/"
        f"{uuid.uuid4()}/bundles/{uuid.uuid4()}/m4c-pre-snapshot"
    )

    assert response.status_code == 401


def test_m4c_snapshot_endpoint_returns_bundle_document_and_no_raw_text(
    monkeypatch,
) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)
    workspace_id = uuid.uuid4()
    bundle_id = uuid.uuid4()
    document_id = uuid.uuid4()
    bundle_row = (
        str(bundle_id),
        "AZ",
        "scorable",
        0.33,
        ["nif", "rccm"],
        "pending",
        False,
        0,
    )
    document_rows = [
        (
            str(document_id),
            68369,
            "658d41cefc0e1fcecfac9f365f1bc2a3",
            "offer_combined",
            0.8,
        )
    ]
    conn = FakeConnection(
        cursors=[
            FakeCursor(row=bundle_row, rows=document_rows),
        ]
    )

    async def fake_connect(*_args, **_kwargs):
        return conn

    with patch.object(mod.psycopg.AsyncConnection, "connect", fake_connect):
        response = client.get(
            "/diagnostics/v1/workspaces/"
            f"{workspace_id}/bundles/{bundle_id}/m4c-pre-snapshot",
            headers={"Authorization": "Bearer secret-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["bundle"]["bundle_id"] == str(bundle_id)
    assert payload["bundle"]["vendor_name_raw"] == "AZ"
    assert payload["document"]["document_id"] == str(document_id)
    assert payload["document"]["raw_text_len"] == 68369
    assert payload["document"]["raw_text_md5"] == "658d41cefc0e1fcecfac9f365f1bc2a3"
    assert payload["document"]["m12_doc_kind"] == "offer_combined"
    assert payload["offer_extractions_count"] == 0
    assert "raw_text" not in payload["document"]
    assert all("raw_text" not in doc for doc in payload["documents"])


def test_m4c_snapshot_endpoint_unknown_bundle_returns_404(monkeypatch) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)
    workspace_id = uuid.uuid4()
    bundle_id = uuid.uuid4()

    async def fake_connect(*_args, **_kwargs):
        return FakeConnection(cursors=[FakeCursor(row=None)])

    with patch.object(mod.psycopg.AsyncConnection, "connect", fake_connect):
        response = client.get(
            "/diagnostics/v1/workspaces/"
            f"{workspace_id}/bundles/{bundle_id}/m4c-pre-snapshot",
            headers={"Authorization": "Bearer secret-token"},
        )

    assert response.status_code == 404
