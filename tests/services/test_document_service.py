from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

import src.services.document_service as document_service


def _sealed_row(session_status: str = "sealed", tamper: bool = False) -> dict:
    snapshot = {
        "process": {"workspace_id": "ws-1"},
        "decision": {"sealed_by": "42"},
        "seal": {},
    }
    digest = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    snapshot["seal"]["seal_hash"] = digest
    if tamper:
        snapshot["decision"]["sealed_by"] = "9999"
    return {
        "id": "sid-1",
        "session_status": session_status,
        "seal_hash": digest,
        "pv_snapshot": snapshot,
        "sealed_at": datetime.now(UTC),
    }


def test_document_service_409_non_sealed(monkeypatch) -> None:
    monkeypatch.setattr(
        document_service,
        "db_execute_one",
        lambda *_args, **_kwargs: _sealed_row(session_status="active"),
    )
    with pytest.raises(HTTPException) as exc:
        document_service.get_sealed_session(object(), "ws-1")
    assert exc.value.status_code == 409


def test_document_service_500_hash_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(
        document_service,
        "db_execute_one",
        lambda *_args, **_kwargs: _sealed_row(session_status="sealed", tamper=True),
    )
    with pytest.raises(HTTPException) as exc:
        document_service.get_sealed_session(object(), "ws-1")
    assert exc.value.status_code == 500


def test_document_service_200_ok(monkeypatch) -> None:
    monkeypatch.setattr(
        document_service,
        "db_execute_one",
        lambda *_args, **_kwargs: _sealed_row(session_status="sealed"),
    )
    out = document_service.get_sealed_session(object(), "ws-1")
    assert out["session_id"] == "sid-1"
    assert len(out["seal_hash"]) == 64
    assert "pv_snapshot" in out
