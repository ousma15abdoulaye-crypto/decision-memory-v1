"""
Core dependencies and helper functions for Decision Memory System.
Storage, artifacts, and memory management.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile

from src.core.config import UPLOADS_DIR
from src.db import db_execute, db_fetchall, get_connection


# =========================
# Storage Helpers
# =========================
def safe_save_upload(case_id: str, kind: str, up: UploadFile) -> tuple[str, str]:
    ext = Path(up.filename).suffix.lower()
    if ext not in [".pdf", ".docx", ".xlsx"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    file_id = str(uuid.uuid4())
    filename = f"{kind}_{file_id}{ext}"
    out_dir = UPLOADS_DIR / case_id
    out_dir.mkdir(parents=True, exist_ok=True)
    full_path = out_dir / filename

    with full_path.open("wb") as f:
        f.write(up.file.read())

    return filename, str(full_path)


def register_artifact(
    case_id: str, kind: str, filename: str, path: str, meta: dict | None = None
) -> str:
    artifact_id = str(uuid.uuid4())
    with get_connection() as conn:
        db_execute(
            conn,
            """
            INSERT INTO artifacts (id, case_id, kind, filename, path, uploaded_at, meta_json)
            VALUES (:aid, :cid, :kind, :fname, :path, :ts, :meta)
        """,
            {
                "aid": artifact_id,
                "cid": case_id,
                "kind": kind,
                "fname": filename,
                "path": path,
                "ts": datetime.utcnow().isoformat(),
                "meta": json.dumps(meta or {}, ensure_ascii=False),
            },
        )
    return artifact_id


def get_artifacts(case_id: str, kind: str | None = None) -> list[dict]:
    with get_connection() as conn:
        if kind:
            rows = db_fetchall(
                conn,
                """
                SELECT * FROM artifacts WHERE case_id=:cid AND kind=:kind ORDER BY uploaded_at DESC
            """,
                {"cid": case_id, "kind": kind},
            )
        else:
            rows = db_fetchall(
                conn,
                "SELECT * FROM artifacts WHERE case_id=:cid ORDER BY uploaded_at DESC",
                {"cid": case_id},
            )
    return rows


def add_memory(case_id: str, entry_type: str, content: dict) -> str:
    mem_id = str(uuid.uuid4())
    with get_connection() as conn:
        db_execute(
            conn,
            """
            INSERT INTO memory_entries (id, case_id, entry_type, content_json, created_at)
            VALUES (:mid, :cid, :etype, :content, :ts)
        """,
            {
                "mid": mem_id,
                "cid": case_id,
                "etype": entry_type,
                "content": json.dumps(content, ensure_ascii=False),
                "ts": datetime.utcnow().isoformat(),
            },
        )
    return mem_id


def list_memory(case_id: str, entry_type: str | None = None) -> list[dict]:
    with get_connection() as conn:
        if entry_type:
            rows = db_fetchall(
                conn,
                """
                SELECT * FROM memory_entries WHERE case_id=:cid AND entry_type=:etype ORDER BY created_at DESC
            """,
                {"cid": case_id, "etype": entry_type},
            )
        else:
            rows = db_fetchall(
                conn,
                """
                SELECT * FROM memory_entries WHERE case_id=:cid ORDER BY created_at DESC
            """,
                {"cid": case_id},
            )
    return [dict(r) | {"content": json.loads(r["content_json"])} for r in rows]
