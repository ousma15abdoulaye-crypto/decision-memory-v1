from __future__ import annotations

import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.assembler.document_rehydration_service import (
    RehydrationStatus,
    rehydrate_bundle_document_raw_text,
)


class FakeConnection:
    def __init__(self, row: dict | None):
        self.row = row
        self.executed: list[tuple[str, dict]] = []
        self.workspace_zip_r2_key = ""


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
        "file_type": "native_pdf",
        "storage_path": "dummy.pdf",
        "raw_text": None,
    }
    row.update(overrides)
    return row


def _patch_db(conn: FakeConnection):
    def fake_execute_one(_conn, sql, _params):
        if "FROM process_workspaces" in sql:
            return {"zip_r2_key": conn.workspace_zip_r2_key}
        return conn.row

    def fake_execute(_conn, sql, params):
        conn.executed.append((sql, params))

    return (
        patch(
            "src.assembler.document_rehydration_service.get_connection",
            return_value=FakeConnectionContext(conn),
        ),
        patch(
            "src.assembler.document_rehydration_service.db_execute_one",
            side_effect=fake_execute_one,
        ),
        patch(
            "src.assembler.document_rehydration_service.db_execute",
            side_effect=fake_execute,
        ),
    )


@pytest.mark.asyncio
async def test_native_pdf_valid_storage_path_updates_raw_text() -> None:
    document_id, workspace_id = _ids()
    conn = FakeConnection(_row(document_id, workspace_id))
    db_patches = _patch_db(conn)

    with (
        db_patches[0],
        db_patches[1],
        db_patches[2],
        patch.object(Path, "is_file", return_value=True),
        patch(
            "src.assembler.ocr_mistral.ocr_native_pdf",
            new=AsyncMock(
                return_value={
                    "raw_text": "Extracted native PDF text",
                    "ocr_engine": "none",
                    "confidence": 1.0,
                }
            ),
        ),
    ):
        result = await rehydrate_bundle_document_raw_text(document_id, workspace_id)

    assert result.status == RehydrationStatus.SUCCESS
    assert result.updated is True
    assert result.ocr_engine == "none"
    assert conn.executed
    update_params = conn.executed[0][1]
    assert update_params["raw_text"] == "Extracted native PDF text"
    assert update_params["ocr_engine"] == "none"
    assert update_params["extracted_at"] is not None


@pytest.mark.asyncio
async def test_existing_raw_text_is_skipped_without_force() -> None:
    document_id, workspace_id = _ids()
    conn = FakeConnection(_row(document_id, workspace_id, raw_text="Already there"))
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2]:
        result = await rehydrate_bundle_document_raw_text(document_id, workspace_id)

    assert result.status == RehydrationStatus.SKIPPED_ALREADY_HAS_TEXT
    assert result.updated is False
    assert conn.executed == []


@pytest.mark.asyncio
async def test_missing_storage_path_returns_status_without_write() -> None:
    document_id, workspace_id = _ids()
    conn = FakeConnection(_row(document_id, workspace_id, storage_path=""))
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2]:
        result = await rehydrate_bundle_document_raw_text(document_id, workspace_id)

    assert result.status == RehydrationStatus.STORAGE_PATH_MISSING
    assert conn.executed == []


@pytest.mark.asyncio
async def test_scan_or_image_uses_mistral_and_updates_raw_text() -> None:
    document_id, workspace_id = _ids()
    conn = FakeConnection(_row(document_id, workspace_id, file_type="scan"))
    db_patches = _patch_db(conn)

    with (
        db_patches[0],
        db_patches[1],
        db_patches[2],
        patch.object(Path, "is_file", return_value=True),
        patch(
            "src.assembler.ocr_mistral.ocr_with_mistral",
            new=AsyncMock(
                return_value={
                    "raw_text": "Extracted OCR text",
                    "ocr_engine": "mistral_ocr_3",
                    "confidence": 0.85,
                }
            ),
        ),
    ):
        result = await rehydrate_bundle_document_raw_text(document_id, workspace_id)

    assert result.status == RehydrationStatus.SUCCESS
    assert result.ocr_engine == "mistral_ocr_3"
    assert conn.executed[0][1]["raw_text"] == "Extracted OCR text"


@pytest.mark.asyncio
async def test_inaccessible_storage_path_falls_back_to_workspace_r2_zip() -> None:
    document_id, workspace_id = _ids()
    conn = FakeConnection(
        _row(
            document_id,
            workspace_id,
            filename="Offre Technique.pdf",
            storage_path="/gcf/az/offre_technique.pdf",
        )
    )
    conn.workspace_zip_r2_key = "workspace.zip"
    db_patches = _patch_db(conn)

    zip_bytes = BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("AZ/Offre Technique.pdf", b"%PDF-1.4 fake")
    zip_bytes.seek(0)

    class Body(BytesIO):
        def close(self) -> None:
            super().close()

    class Settings:
        R2_BUCKET_NAME = "bucket"

        def r2_object_storage_configured(self) -> bool:
            return True

    class S3:
        def get_object(self, **_kwargs):
            return {"Body": Body(zip_bytes.getvalue())}

    with (
        db_patches[0],
        db_patches[1],
        db_patches[2],
        patch.object(Path, "is_file", side_effect=[False, True]),
        patch(
            "src.assembler.document_rehydration_service.get_settings",
            return_value=Settings(),
        ),
        patch(
            "src.assembler.document_rehydration_service.make_r2_s3_client",
            return_value=S3(),
        ),
        patch(
            "src.assembler.ocr_mistral.ocr_native_pdf",
            new=AsyncMock(
                return_value={
                    "raw_text": "Extracted text from R2 zip",
                    "ocr_engine": "none",
                    "confidence": 1.0,
                }
            ),
        ),
    ):
        result = await rehydrate_bundle_document_raw_text(document_id, workspace_id)

    assert result.status == RehydrationStatus.SUCCESS
    assert conn.executed[0][1]["raw_text"] == "Extracted text from R2 zip"


@pytest.mark.asyncio
async def test_workspace_mismatch_refuses_without_write() -> None:
    document_id, actual_workspace_id = _ids()
    requested_workspace_id = uuid.uuid4()
    conn = FakeConnection(_row(document_id, actual_workspace_id))
    db_patches = _patch_db(conn)

    with db_patches[0], db_patches[1], db_patches[2]:
        result = await rehydrate_bundle_document_raw_text(
            document_id, requested_workspace_id
        )

    assert result.status == RehydrationStatus.WORKSPACE_MISMATCH
    assert conn.executed == []
