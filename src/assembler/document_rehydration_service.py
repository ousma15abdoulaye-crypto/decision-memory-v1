"""Non-destructive raw_text rehydration for existing bundle_documents."""

from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

from src.assembler.pdf_detector import FileType, detect_file_type
from src.core.config import get_settings, make_r2_s3_client
from src.db import db_execute, db_execute_one, get_connection

logger = logging.getLogger(__name__)


class RehydrationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    SKIPPED_ALREADY_HAS_TEXT = "SKIPPED_ALREADY_HAS_TEXT"
    STORAGE_PATH_MISSING = "STORAGE_PATH_MISSING"
    FILE_NOT_ACCESSIBLE = "FILE_NOT_ACCESSIBLE"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    WORKSPACE_MISMATCH = "WORKSPACE_MISMATCH"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"


@dataclass(frozen=True)
class RehydrationResult:
    status: RehydrationStatus
    workspace_id: str
    document_id: str
    raw_text_len: int = 0
    ocr_engine: str | None = None
    ocr_confidence: float | None = None
    updated: bool = False
    error: str | None = None

    def log_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "workspace_id": self.workspace_id,
            "document_id": self.document_id,
            "raw_text_len": self.raw_text_len,
            "ocr_engine": self.ocr_engine,
            "ocr_confidence": self.ocr_confidence,
            "updated": self.updated,
            "error": self.error,
        }


async def _extract_raw_text(
    file_path: Path, stored_file_type: str | None
) -> dict[str, Any]:
    file_type = _resolve_file_type(file_path, stored_file_type)

    if file_type == FileType.NATIVE_PDF:
        from src.assembler.ocr_mistral import ocr_native_pdf

        return await ocr_native_pdf(file_path)
    if file_type in {FileType.SCAN, FileType.IMAGE}:
        from src.assembler.ocr_mistral import ocr_with_mistral

        return await ocr_with_mistral(file_path)
    if file_type == FileType.WORD:
        from src.assembler.graph import _extract_word

        return _extract_word(file_path)
    if file_type == FileType.EXCEL:
        from src.assembler.graph import _extract_excel

        return _extract_excel(file_path)

    return {
        "raw_text": "",
        "confidence": 0.0,
        "ocr_engine": None,
        "error": f"Unsupported file_type={file_type.value}",
    }


def _resolve_file_type(file_path: Path, stored_file_type: str | None) -> FileType:
    if stored_file_type:
        normalized = stored_file_type.strip().lower()
        for candidate in FileType:
            if normalized == candidate.value:
                return candidate
    return detect_file_type(file_path)


def _normalized_name(value: str | None) -> str:
    return (value or "").strip().replace("\\", "/").split("/")[-1].lower()


def _pick_zip_member(
    zf: zipfile.ZipFile, filename: str, storage_path: str
) -> str | None:
    wanted = {_normalized_name(filename), _normalized_name(storage_path)}
    wanted.discard("")
    candidates = [name for name in zf.namelist() if not name.endswith("/")]
    for name in candidates:
        if _normalized_name(name) in wanted:
            return name
    return None


@contextmanager
def _provided_path(path: Path | None) -> Iterator[Path | None]:
    yield path


@contextmanager
def _document_file_from_workspace_zip(
    conn: Any,
    workspace_id: str,
    filename: str,
    storage_path: str,
) -> Iterator[Path | None]:
    row = db_execute_one(
        conn,
        """
        SELECT zip_r2_key
        FROM process_workspaces
        WHERE id = CAST(:workspace_id AS uuid)
        """,
        {"workspace_id": workspace_id},
    )
    r2_key = ((row or {}).get("zip_r2_key") or "").strip()
    if not r2_key:
        yield None
        return

    settings = get_settings()
    if not settings.r2_object_storage_configured():
        yield None
        return

    s3 = make_r2_s3_client()
    obj = s3.get_object(Bucket=settings.R2_BUCKET_NAME, Key=r2_key)
    body = obj["Body"]
    zip_tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    zip_tmp.close()
    extracted_tmp: tempfile.NamedTemporaryFile | None = None
    try:
        with open(zip_tmp.name, "wb") as out_f:
            shutil.copyfileobj(body, out_f, length=1024 * 1024)
        with zipfile.ZipFile(zip_tmp.name) as zf:
            member = _pick_zip_member(zf, filename, storage_path)
            if not member:
                yield None
                return
            suffix = Path(member).suffix or Path(filename).suffix or ".bin"
            extracted_tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            extracted_tmp.close()
            with zf.open(member) as src, open(extracted_tmp.name, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            yield Path(extracted_tmp.name)
    finally:
        try:
            body.close()
        except Exception:
            pass
        Path(zip_tmp.name).unlink(missing_ok=True)
        if extracted_tmp is not None:
            Path(extracted_tmp.name).unlink(missing_ok=True)


async def rehydrate_bundle_document_raw_text(
    document_id: UUID,
    workspace_id: UUID,
    force: bool = False,
) -> RehydrationResult:
    """Recompute raw_text for one existing bundle_document without changing its bundle.

    Only the document extraction fields are updated. Supplier bundles, scoring,
    matrices, and assessments are intentionally untouched.
    """
    document_id_str = str(document_id)
    workspace_id_str = str(workspace_id)

    with get_connection() as conn:
        row = db_execute_one(
            conn,
            """
            SELECT id::text AS id,
                   workspace_id::text AS workspace_id,
                   filename,
                   file_type,
                   storage_path,
                   raw_text
            FROM bundle_documents
            WHERE id = CAST(:document_id AS uuid)
            """,
            {"document_id": document_id_str},
        )

        if not row:
            return RehydrationResult(
                status=RehydrationStatus.DOCUMENT_NOT_FOUND,
                workspace_id=workspace_id_str,
                document_id=document_id_str,
            )

        if str(row["workspace_id"]) != workspace_id_str:
            return RehydrationResult(
                status=RehydrationStatus.WORKSPACE_MISMATCH,
                workspace_id=workspace_id_str,
                document_id=document_id_str,
            )

        existing_text = row.get("raw_text")
        if isinstance(existing_text, str) and existing_text.strip() and not force:
            return RehydrationResult(
                status=RehydrationStatus.SKIPPED_ALREADY_HAS_TEXT,
                workspace_id=workspace_id_str,
                document_id=document_id_str,
                raw_text_len=len(existing_text),
                updated=False,
            )

        storage_path = (row.get("storage_path") or "").strip()
        if not storage_path:
            return RehydrationResult(
                status=RehydrationStatus.STORAGE_PATH_MISSING,
                workspace_id=workspace_id_str,
                document_id=document_id_str,
            )

        file_path: Path | None = Path(storage_path)
        if not file_path.is_file():
            file_path = None

        if file_path is None:
            zip_file = _document_file_from_workspace_zip(
                conn,
                workspace_id_str,
                row.get("filename") or "",
                storage_path,
            )
        else:
            zip_file = None

        with (
            zip_file if zip_file is not None else _provided_path(file_path)
        ) as resolved:
            if resolved is None or not resolved.is_file():
                return RehydrationResult(
                    status=RehydrationStatus.FILE_NOT_ACCESSIBLE,
                    workspace_id=workspace_id_str,
                    document_id=document_id_str,
                )

            extraction = await _extract_raw_text(resolved, row.get("file_type"))

        raw_text = extraction.get("raw_text")
        if isinstance(raw_text, str):
            raw_text = raw_text.replace("\x00", "")
        else:
            raw_text = ""

        engine = extraction.get("ocr_engine")
        confidence = extraction.get("confidence")
        if not raw_text.strip():
            status = (
                RehydrationStatus.UNSUPPORTED_FILE_TYPE
                if extraction.get("error", "").startswith("Unsupported file_type=")
                else RehydrationStatus.EXTRACTION_FAILED
            )
            return RehydrationResult(
                status=status,
                workspace_id=workspace_id_str,
                document_id=document_id_str,
                ocr_engine=engine,
                ocr_confidence=confidence,
                error=extraction.get("error"),
            )

        db_execute(
            conn,
            """
            UPDATE bundle_documents
            SET raw_text = :raw_text,
                ocr_engine = :ocr_engine,
                ocr_confidence = :ocr_confidence,
                extracted_at = :extracted_at
            WHERE id = CAST(:document_id AS uuid)
              AND workspace_id = CAST(:workspace_id AS uuid)
            """,
            {
                "raw_text": raw_text,
                "ocr_engine": engine,
                "ocr_confidence": confidence,
                "extracted_at": datetime.now(UTC),
                "document_id": document_id_str,
                "workspace_id": workspace_id_str,
            },
        )

    logger.info(
        "[REHYDRATE] bundle_document workspace=%s document=%s status=%s len=%d engine=%s",
        workspace_id_str,
        document_id_str,
        RehydrationStatus.SUCCESS.value,
        len(raw_text),
        engine,
    )
    return RehydrationResult(
        status=RehydrationStatus.SUCCESS,
        workspace_id=workspace_id_str,
        document_id=document_id_str,
        raw_text_len=len(raw_text),
        ocr_engine=engine,
        ocr_confidence=confidence,
        updated=True,
    )
