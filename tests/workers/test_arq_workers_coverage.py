"""Couverture ciblée — workers ARQ + workspace (CI fail_under 68 %)."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import MagicMock, patch

import pytest


def test_workspace_status_transitions_reexports() -> None:
    import src.workspace.status_transitions as st

    assert "validate_transition" in st.__all__
    assert st.CognitiveFacts is not None


def test_arq_config_settings_and_worker_settings() -> None:
    from src.workers import arq_config

    s = arq_config.get_arq_settings()
    assert isinstance(s.redis_url, str)
    assert s.max_jobs == 10
    assert arq_config.WorkerSettings.job_timeout == 300
    assert len(arq_config.WorkerSettings.functions) >= 5


@pytest.mark.asyncio
async def test_project_sealed_workspace_missing_workspace() -> None:
    from src.workers.arq_sealed_workspace import project_sealed_workspace

    mock_conn = MagicMock()
    mock_conn.fetchone.return_value = None
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_conn)
    ctx.__exit__ = MagicMock(return_value=False)

    with patch("src.db.get_connection", return_value=ctx):
        out = await project_sealed_workspace({}, str(uuid.uuid4()))
    assert out["signals"] == 0
    assert out["workspace_id"]


@pytest.mark.asyncio
async def test_project_workspace_events_to_couche_b_no_pending() -> None:
    from src.workers.arq_projector_couche_b import project_workspace_events_to_couche_b

    mock_conn = MagicMock()
    mock_conn.fetchone.return_value = {"max": None}
    mock_conn.fetchall.return_value = []
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_conn)
    ctx.__exit__ = MagicMock(return_value=False)

    with patch("src.db.get_connection", return_value=ctx):
        out = await project_workspace_events_to_couche_b({})
    assert out["ok"] == 0
    assert out["failed"] == 0
    assert out["last_event_id"] == 0


def test_arq_worker_on_startup_uses_uploads_when_no_r2() -> None:
    from pathlib import Path

    from src.core import config as core_config
    from src.workers.arq_config import arq_worker_on_startup

    class _S:
        def r2_object_storage_configured(self) -> bool:
            return False

        UPLOADS_DIR = str(Path.cwd() / "tmp_arq_uploads_test")

    with patch.object(core_config, "get_settings", lambda: _S()):
        asyncio.run(arq_worker_on_startup({}))


@pytest.mark.asyncio
async def test_run_pass_minus_1_missing_zip_key() -> None:
    from src.workers.arq_tasks import run_pass_minus_1

    wid, tid = str(uuid.uuid4()), str(uuid.uuid4())

    mock_conn = MagicMock()

    def _fake_one(_conn, _sql, _params=None):
        return None

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_conn)
    ctx.__exit__ = MagicMock(return_value=False)

    with (
        patch("src.db.tenant_context.set_db_tenant_id", lambda *_a, **_k: None),
        patch("src.db.tenant_context.set_rls_is_admin", lambda *_a, **_k: None),
        patch(
            "src.db.tenant_context.reset_rls_request_context", lambda *_a, **_k: None
        ),
        patch("src.db.get_connection", return_value=ctx),
        patch("src.db.db_execute_one", side_effect=_fake_one),
    ):
        out = await run_pass_minus_1({}, wid, tid, zip_path="", zip_r2_key="")

    assert out["bundle_ids"] == []
    assert out.get("error")
