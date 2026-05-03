from __future__ import annotations

import uuid
from unittest.mock import patch

from src.assembler.document_m12_service import (
    M12ClassificationStatus,
    classify_bundle_document_m12,
)


class FakeConnection:
    def __init__(self, row: dict | None):
        self.row = row
        self.executed: list[tuple[str, dict]] = []


class FakeConnectionContext:
    def __init__(self, conn: FakeConnection):
        self.conn = conn

    def __enter__(self) -> FakeConnection:
        return self.conn

    def __exit__(self, *_args) -> bool:
        return False


def _ids() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


def _row(document_id: uuid.UUID, workspace_id: uuid.UUID, **overrides) -> dict:
    row = {
        "id": str(document_id),
        "workspace_id": str(workspace_id),
        "filename": "Offre Technique.pdf",
        "raw_text": "OFFRE TECHNIQUE\nPrix total et montant de l'offre",
        "m12_doc_kind": None,
        "m12_confidence": None,
        "m12_evidence": None,
    }
    row.update(overrides)
    return row


def _patch_db(conn: FakeConnection):
    def fake_execute_one(_conn, _sql, _params):
        return conn.row

    def fake_execute(_conn, sql, params):
        conn.executed.append((sql, params))

    return (
        patch(
            "src.assembler.document_m12_service.get_connection",
            return_value=FakeConnectionContext(conn),
        ),
        patch(
            "src.assembler.document_m12_service.db_execute_one",
            side_effect=fake_execute_one,
        ),
        patch(
            "src.assembler.document_m12_service.db_execute",
            side_effect=fake_execute,
        ),
    )


def test_classifies_existing_document_and_updates_only_m12_columns() -> None:
    document_id, workspace_id = _ids()
    conn = FakeConnection(_row(document_id, workspace_id))
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2]:
        result = classify_bundle_document_m12(document_id, workspace_id)

    assert result.status == M12ClassificationStatus.SUCCESS
    assert result.updated is True
    assert result.m12_doc_kind == "offer_combined"
    assert result.m12_confidence == 0.8
    assert conn.executed
    sql, params = conn.executed[0]
    assert "m12_doc_kind" in sql
    assert "m12_confidence" in sql
    assert "m12_evidence" in sql
    assert "raw_text =" not in sql
    assert params["m12_doc_kind"] == "offer_combined"
    assert params["m12_confidence"] == 0.8
    assert "source=classify_document_type_for_pass_minus_one" in params["m12_evidence"]


def test_existing_m12_is_skipped_without_force() -> None:
    document_id, workspace_id = _ids()
    conn = FakeConnection(
        _row(
            document_id,
            workspace_id,
            m12_doc_kind="offer_combined",
            m12_confidence=0.8,
            m12_evidence=["existing"],
        )
    )
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2]:
        result = classify_bundle_document_m12(document_id, workspace_id)

    assert result.status == M12ClassificationStatus.SKIPPED_ALREADY_CLASSIFIED
    assert result.updated is False
    assert conn.executed == []


def test_missing_raw_text_returns_status_without_write() -> None:
    document_id, workspace_id = _ids()
    conn = FakeConnection(_row(document_id, workspace_id, raw_text=""))
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2]:
        result = classify_bundle_document_m12(document_id, workspace_id)

    assert result.status == M12ClassificationStatus.RAW_TEXT_MISSING
    assert result.updated is False
    assert conn.executed == []


def test_workspace_mismatch_returns_status_without_write() -> None:
    document_id, workspace_id = _ids()
    conn = FakeConnection(_row(document_id, uuid.uuid4()))
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2]:
        result = classify_bundle_document_m12(document_id, workspace_id)

    assert result.status == M12ClassificationStatus.WORKSPACE_MISMATCH
    assert conn.executed == []
