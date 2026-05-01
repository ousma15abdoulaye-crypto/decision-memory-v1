from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock, patch

from src.procurement.bundle_offer_extraction_service import (
    BundleOfferExtractionStatus,
    extract_supplier_bundle_offer,
)


class FakeConnection:
    def __init__(
        self,
        bundle: dict | None,
        rows: list[dict] | None,
        existing: dict | None = None,
        saved: dict | None = None,
    ):
        self.bundle = bundle
        self.rows = rows or []
        self.existing = existing
        self.saved = saved or {"id": "extraction-1", "supplier_name": "AZ"}
        self.one_calls = 0


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
        "gate_b_role": "scorable",
        "legacy_case_id": "case-1",
    }
    row.update(overrides)
    return row


def _doc(**overrides) -> dict:
    row = {
        "id": str(uuid.uuid4()),
        "doc_type": "offer_technical",
        "filename": "Offre Technique.pdf",
        "raw_text": "OFFRE TECHNIQUE\nPrix total et montant de l'offre",
        "m12_doc_kind": "offer_combined",
        "bundle_id": str(uuid.uuid4()),
    }
    row.update(overrides)
    return row


def _patch_db(conn: FakeConnection):
    def fake_execute_one(_conn, sql, _params):
        conn.one_calls += 1
        if "FROM supplier_bundles" in sql:
            return conn.bundle
        if "FROM offer_extractions" in sql and conn.one_calls <= 2:
            return conn.existing
        return conn.saved

    return (
        patch(
            "src.procurement.bundle_offer_extraction_service.get_connection",
            return_value=FakeConnectionContext(conn),
        ),
        patch(
            "src.procurement.bundle_offer_extraction_service.db_execute_one",
            side_effect=fake_execute_one,
        ),
        patch(
            "src.procurement.bundle_offer_extraction_service.db_fetchall",
            return_value=conn.rows,
        ),
    )


def test_extracts_scorable_offer_bundle_without_downstream_writes() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(_bundle(bundle_id, workspace_id), [_doc()])
    extraction = Mock(extraction_ok=True, error_reason=None)
    persist = Mock()
    db_patches = _patch_db(conn)

    with (
        db_patches[0],
        db_patches[1] as execute_one_mock,
        db_patches[2],
        patch(
            "src.procurement.bundle_offer_extraction_service.extract_offer_content_async",
            AsyncMock(return_value=extraction),
        ) as extract_mock,
        patch(
            "src.procurement.bundle_offer_extraction_service.persist_tdr_result_to_db",
            persist,
        ),
    ):
        result = extract_supplier_bundle_offer(workspace_id, bundle_id)

    assert result.status == BundleOfferExtractionStatus.SUCCESS
    assert result.updated is True
    assert result.extraction_id == "extraction-1"
    extract_mock.assert_awaited_once()
    persist.assert_called_once_with(
        extraction,
        "case-1",
        str(bundle_id),
        workspace_id=str(workspace_id),
    )
    for call in execute_one_mock.mock_calls:
        sql = call.args[1]
        assert "evaluation_documents" not in sql
        assert "criterion_assessments" not in sql
        assert "run_pipeline_v5" not in sql


def test_non_scorable_bundle_is_rejected_without_extraction() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(
        _bundle(bundle_id, workspace_id, gate_b_role="reference"),
        [_doc()],
    )
    db_patches = _patch_db(conn)
    extract = AsyncMock()

    with (
        db_patches[0],
        db_patches[1],
        db_patches[2],
        patch(
            "src.procurement.bundle_offer_extraction_service.extract_offer_content_async",
            extract,
        ),
    ):
        result = extract_supplier_bundle_offer(workspace_id, bundle_id)

    assert result.status == BundleOfferExtractionStatus.NOT_SCORABLE
    extract.assert_not_called()


def test_missing_raw_text_returns_status_without_extraction() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(_bundle(bundle_id, workspace_id), [_doc(raw_text="")])
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2]:
        result = extract_supplier_bundle_offer(workspace_id, bundle_id)

    assert result.status == BundleOfferExtractionStatus.RAW_TEXT_MISSING


def test_missing_m12_returns_status_without_extraction() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(_bundle(bundle_id, workspace_id), [_doc(m12_doc_kind=None)])
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2]:
        result = extract_supplier_bundle_offer(workspace_id, bundle_id)

    assert result.status == BundleOfferExtractionStatus.M12_MISSING


def test_no_offer_document_returns_status_without_extraction() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(
        _bundle(bundle_id, workspace_id),
        [_doc(doc_type="nif", m12_doc_kind="nif")],
    )
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2]:
        result = extract_supplier_bundle_offer(workspace_id, bundle_id)

    assert result.status == BundleOfferExtractionStatus.NO_OFFER_DOCUMENT


def test_existing_extraction_is_skipped_without_force() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(
        _bundle(bundle_id, workspace_id),
        [_doc()],
        existing={"id": "existing-1", "supplier_name": "AZ"},
    )
    db_patches = _patch_db(conn)
    extract = AsyncMock()

    with (
        db_patches[0],
        db_patches[1],
        db_patches[2],
        patch(
            "src.procurement.bundle_offer_extraction_service.extract_offer_content_async",
            extract,
        ),
    ):
        result = extract_supplier_bundle_offer(workspace_id, bundle_id)

    assert result.status == BundleOfferExtractionStatus.SKIPPED_ALREADY_EXTRACTED
    assert result.extraction_id == "existing-1"
    extract.assert_not_called()


def test_backend_failure_returns_extraction_failed_without_persistence() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(_bundle(bundle_id, workspace_id), [_doc()])
    extraction = Mock(extraction_ok=False, error_reason="backend_timeout")
    persist = Mock()
    db_patches = _patch_db(conn)

    with (
        db_patches[0],
        db_patches[1],
        db_patches[2],
        patch(
            "src.procurement.bundle_offer_extraction_service.extract_offer_content_async",
            AsyncMock(return_value=extraction),
        ),
        patch(
            "src.procurement.bundle_offer_extraction_service.persist_tdr_result_to_db",
            persist,
        ),
    ):
        result = extract_supplier_bundle_offer(workspace_id, bundle_id)

    assert result.status == BundleOfferExtractionStatus.EXTRACTION_FAILED
    persist.assert_not_called()


def test_persistence_failure_returns_persistence_failed() -> None:
    workspace_id, bundle_id = _ids()
    conn = FakeConnection(_bundle(bundle_id, workspace_id), [_doc()])
    extraction = Mock(extraction_ok=True, error_reason=None)
    db_patches = _patch_db(conn)

    with (
        db_patches[0],
        db_patches[1],
        db_patches[2],
        patch(
            "src.procurement.bundle_offer_extraction_service.extract_offer_content_async",
            AsyncMock(return_value=extraction),
        ),
        patch(
            "src.procurement.bundle_offer_extraction_service.persist_tdr_result_to_db",
            side_effect=RuntimeError("db down"),
        ),
    ):
        result = extract_supplier_bundle_offer(workspace_id, bundle_id)

    assert result.status == BundleOfferExtractionStatus.PERSISTENCE_FAILED
