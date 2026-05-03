from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from contextlib import ExitStack, contextmanager
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


class SyncFakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _m6d_offers():
    field = {
        "name": "methodology",
        "value": "Approche",
        "confidence": 0.9,
        "evidence": "source",
    }
    return [
        {
            "document_id": "az-bundle",
            "supplier_name": "A - Z SARL",
            "extraction_id": "az-extraction",
            "extraction_ok": True,
            "review_required": False,
            "taxonomy_core": "offer_technical",
            "family_main": "consultance",
            "family_sub": "technical",
            "extracted_fields": [field],
            "evidence_map": {"methodology": "source"},
            "missing_fields": [],
            "line_items": [],
            "readiness_status": "ready",
            "readiness_blockers": [],
            "readiness_warnings": [],
        },
        {
            "document_id": "atmost-bundle",
            "supplier_name": "ATMOST",
            "extraction_id": "atmost-extraction",
            "extraction_ok": True,
            "review_required": False,
            "taxonomy_core": "dao",
            "family_main": "consultance",
            "family_sub": "technical",
            "extracted_fields": [field],
            "evidence_map": {"methodology": "source"},
            "missing_fields": [],
            "line_items": [],
            "readiness_status": "ready",
            "readiness_blockers": [],
            "readiness_warnings": ["taxonomy_core_divergent"],
        },
    ]


def _m6d_rows(*, dao_count=3, dao_total=100.0, eval_count=0, ca_count=0, stale=False):
    weight = dao_total / dao_count if dao_count else 0
    dao_rows = [
        {
            "id": f"criterion-{index}",
            "critere_nom": f"Criterion {index}",
            "ponderation": weight,
            "is_eliminatory": False,
            "famille": "quality",
            "created_at": "2026-05-01T00:00:00Z",
        }
        for index in range(dao_count)
    ]
    return [
        dao_rows,
        [{"case_id": "case-1"}],
        [{"n": eval_count}],
        [{"n": ca_count}],
        [{"stale": stale}],
    ]


@contextmanager
def _patch_m6d_probe(mod, *, rows=None, offers=None):
    with ExitStack() as stack:
        patches = (
            stack.enter_context(
                patch.object(
                    mod,
                    "open_m6d_readonly_connection",
                    return_value=SyncFakeConnection(),
                )
            ),
            stack.enter_context(
                patch.object(
                    mod,
                    "build_canonical_m14_offers",
                    return_value=offers or _m6d_offers(),
                )
            ),
            stack.enter_context(
                patch.object(mod, "fetch_m6d_rows", side_effect=rows or _m6d_rows())
            ),
            stack.enter_context(
                patch.object(
                    mod, "construct_m14_input_no_persist", return_value=object()
                )
            ),
        )
        yield patches


def test_m6d_builder_probe_requires_bearer(monkeypatch) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)

    response = client.get(
        f"/diagnostics/v1/workspaces/{uuid.uuid4()}/m6d-builder-probe"
    )

    assert response.status_code == 401


def test_m6d_builder_probe_returns_enriched_offers_and_no_raw_text(monkeypatch) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)
    workspace_id = uuid.uuid4()

    with _patch_m6d_probe(mod):
        response = client.get(
            f"/diagnostics/v1/workspaces/{workspace_id}/m6d-builder-probe",
            headers={"Authorization": "Bearer secret-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert "raw_text" not in json.dumps(payload).lower()
    assert payload["offers_count"] == 2
    assert payload["offers"][0]["identity_only"] is False
    assert payload["offers"][0]["readiness_blockers"] == []
    assert payload["offers"][1]["readiness_warnings"] == ["taxonomy_core_divergent"]
    assert payload["forbidden_actions"]["m14_evaluate"] == "NO"
    assert payload["forbidden_actions"]["enqueue"] == "NO"


def test_m6d_m14_input_probe_is_no_persist_and_does_not_call_engine(
    monkeypatch,
) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)
    workspace_id = uuid.uuid4()

    with _patch_m6d_probe(mod) as patches:
        response = client.get(
            f"/diagnostics/v1/workspaces/{workspace_id}/m6d-builder-probe?include_m14_input=true",
            headers={"Authorization": "Bearer secret-token"},
        )

    assert response.status_code == 200
    assert patches[3].called
    probe = response.json()["m14_input_probe"]
    assert probe["no_persist"] is True
    assert probe["evaluation_engine_called"] is False
    assert probe["repository_used"] is False
    assert probe["created_artifacts"] == []
    assert probe["input_ready"] is True


def test_m6d_offer_count_expectation_is_optional(monkeypatch) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)
    workspace_id = uuid.uuid4()

    with _patch_m6d_probe(mod, offers=_m6d_offers()[:1]):
        response = client.get(
            f"/diagnostics/v1/workspaces/{workspace_id}/m6d-builder-probe?include_m14_input=true",
            headers={"Authorization": "Bearer secret-token"},
        )

    probe = response.json()["m14_input_probe"]
    assert probe["offers_count"] == 1
    assert "offers_count_mismatch" not in probe["input_blockers"]
    assert probe["input_ready"] is True


def test_m6d_input_ready_false_for_bad_dao_weights(monkeypatch) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)
    workspace_id = uuid.uuid4()

    with _patch_m6d_probe(mod, rows=_m6d_rows(dao_count=3, dao_total=90.0)):
        response = client.get(
            f"/diagnostics/v1/workspaces/{workspace_id}/m6d-builder-probe?include_m14_input=true",
            headers={"Authorization": "Bearer secret-token"},
        )

    probe = response.json()["m14_input_probe"]
    assert probe["input_ready"] is False
    assert "dao_weights_total_mismatch" in probe["input_blockers"]


def test_m6d_input_ready_false_for_offer_count_mismatch(monkeypatch) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)
    workspace_id = uuid.uuid4()

    with _patch_m6d_probe(mod):
        response = client.get(
            f"/diagnostics/v1/workspaces/{workspace_id}/m6d-builder-probe"
            "?include_m14_input=true&expected_offers_count=3",
            headers={"Authorization": "Bearer secret-token"},
        )

    probe = response.json()["m14_input_probe"]
    assert probe["input_ready"] is False
    assert "offers_count_mismatch" in probe["input_blockers"]


def test_open_m6d_readonly_connection_begins_read_only_then_admin_guc(
    monkeypatch,
) -> None:
    """M6H2: diagnostics DB path must use a DB-enforced read-only transaction."""
    import src.db.core as db_core
    import src.resilience as resilience_mod

    stmts: list[tuple[str, object | None]] = []

    class _FakeCur:
        def execute(self, sql, params=None):
            stmts.append((sql.strip(), params))

        def close(self) -> None:
            return None

    class _FakeConn:
        def __init__(self) -> None:
            self._cur = _FakeCur()

        def cursor(self, row_factory=None):
            return self._cur

        def commit(self) -> None:
            return None

        def rollback(self) -> None:
            return None

        def close(self) -> None:
            return None

    fake = _FakeConn()
    monkeypatch.setattr(db_core, "_get_raw_connection", lambda: fake)
    monkeypatch.setattr(resilience_mod.db_breaker, "call", lambda fn: fn())

    mod = _load_worker_module(monkeypatch)
    with mod.open_m6d_readonly_connection():
        pass

    assert len(stmts) >= 2
    assert stmts[0][0].upper().startswith("BEGIN READ ONLY")
    lowered = stmts[1][0].lower()
    assert "set_config" in lowered and "app.is_admin" in lowered
    assert stmts[1][1] == {"v": "true"}


def test_m6d_reports_stale_criterion_assessments(monkeypatch) -> None:
    mod = _load_worker_module(monkeypatch)
    client = TestClient(mod.app)
    workspace_id = uuid.uuid4()

    with _patch_m6d_probe(mod, rows=_m6d_rows(ca_count=6, stale=True)):
        response = client.get(
            f"/diagnostics/v1/workspaces/{workspace_id}/m6d-builder-probe?include_m14_input=true",
            headers={"Authorization": "Bearer secret-token"},
        )

    payload = response.json()
    assert payload["stale_assessments_exist"] is True
    assert payload["criterion_assessments_count"] == 6
    assert (
        "criterion_assessments_historical_contamination_risk"
        in payload["m14_input_probe"]["input_blockers"]
    )
