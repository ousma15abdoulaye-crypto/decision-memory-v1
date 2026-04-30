from __future__ import annotations

import uuid
from unittest.mock import patch

from src.procurement.bundle_gate_b_service import (
    BundleGateBQualificationStatus,
    qualify_supplier_bundle_gate_b,
)


class FakeConnection:
    def __init__(self, bundle: dict | None, rows: list[dict] | None):
        self.bundle = bundle
        self.rows = rows or []
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


def _bundle(bundle_id: uuid.UUID, workspace_id: uuid.UUID, **overrides) -> dict:
    row = {
        "id": str(bundle_id),
        "workspace_id": str(workspace_id),
        "vendor_name_raw": "AZ",
        "gate_b_role": None,
        "gate_b_reason_codes": [],
        "qualification_status": "pending",
        "completeness_score": None,
        "missing_documents": None,
    }
    row.update(overrides)
    return row


def _doc(**overrides) -> dict:
    row = {
        "id": str(uuid.uuid4()),
        "doc_type": "offer_technical",
        "doc_role": "primary",
        "filename": "Offre Technique.pdf",
        "raw_text": "OFFRE TECHNIQUE\nPrix total et montant de l'offre",
        "m12_doc_kind": "offer_combined",
        "m12_confidence": 0.8,
        "bundle_id": str(uuid.uuid4()),
    }
    row.update(overrides)
    return row


def _patch_db(conn: FakeConnection):
    def fake_execute_one(_conn, _sql, _params):
        return conn.bundle

    def fake_fetchall(_conn, _sql, _params):
        return conn.rows

    def fake_execute(_conn, sql, params):
        conn.executed.append((sql, params))

    return (
        patch(
            "src.procurement.bundle_gate_b_service.get_connection",
            return_value=FakeConnectionContext(conn),
        ),
        patch(
            "src.procurement.bundle_gate_b_service.db_execute_one",
            side_effect=fake_execute_one,
        ),
        patch(
            "src.procurement.bundle_gate_b_service.db_fetchall",
            side_effect=fake_fetchall,
        ),
        patch(
            "src.procurement.bundle_gate_b_service.db_execute",
            side_effect=fake_execute,
        ),
    )


def test_qualifies_scorable_offer_bundle_without_touching_scoring() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(_bundle(bundle_id, workspace_id), [_doc()])
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2], db_patches[3]:
        result = qualify_supplier_bundle_gate_b(workspace_id, bundle_id)

    assert result.status == BundleGateBQualificationStatus.SUCCESS
    assert result.updated is True
    assert result.gate_b_role == "scorable"
    assert result.gate_b_reason_codes == ["supplier_offer_with_present_raw_text"]
    assert result.qualification_status == "qualified"
    assert result.completeness_score == 1 / 3
    assert result.missing_documents == ["nif", "rccm"]
    assert conn.executed
    sql, params = conn.executed[0]
    assert "gate_b_role" in sql
    assert "gate_b_reason_codes" in sql
    assert "gate_b_evaluated_at" in sql
    assert "gate_b_evaluated_by" in sql
    assert "qualification_status" in sql
    assert "completeness_score" in sql
    assert "raw_text" not in sql
    assert "evaluation_documents" not in sql
    assert "criterion_assessments" not in sql
    assert "matrix" not in sql.lower()
    assert params["gate_b_role"] == "scorable"
    assert params["gate_b_reason_codes"] == ["supplier_offer_with_present_raw_text"]
    assert params["gate_b_evaluated_by"] == "bundle_gate_b_service"


def test_existing_gate_b_role_is_skipped_without_force() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(
        _bundle(
            bundle_id,
            workspace_id,
            gate_b_role="scorable",
            gate_b_reason_codes=["supplier_offer_with_present_raw_text"],
            qualification_status="qualified",
            completeness_score=1 / 3,
            missing_documents=["nif", "rccm"],
        ),
        [_doc()],
    )
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2], db_patches[3]:
        result = qualify_supplier_bundle_gate_b(workspace_id, bundle_id)

    assert result.status == BundleGateBQualificationStatus.SKIPPED_ALREADY_EVALUATED
    assert result.updated is False
    assert conn.executed == []


def test_missing_documents_returns_status_without_write() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(_bundle(bundle_id, workspace_id), [])
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2], db_patches[3]:
        result = qualify_supplier_bundle_gate_b(workspace_id, bundle_id)

    assert result.status == BundleGateBQualificationStatus.DOCUMENTS_MISSING
    assert conn.executed == []


def test_missing_raw_text_returns_status_without_write() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(_bundle(bundle_id, workspace_id), [_doc(raw_text="")])
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2], db_patches[3]:
        result = qualify_supplier_bundle_gate_b(workspace_id, bundle_id)

    assert result.status == BundleGateBQualificationStatus.RAW_TEXT_MISSING
    assert conn.executed == []


def test_missing_m12_returns_status_without_write() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(
        _bundle(bundle_id, workspace_id),
        [_doc(m12_doc_kind=None)],
    )
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2], db_patches[3]:
        result = qualify_supplier_bundle_gate_b(workspace_id, bundle_id)

    assert result.status == BundleGateBQualificationStatus.M12_MISSING
    assert conn.executed == []
