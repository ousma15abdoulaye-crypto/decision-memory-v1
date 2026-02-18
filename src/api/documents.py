"""
Document upload, download, and memory endpoints.
"""

import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.core.dependencies import (
    get_artifacts,
    list_memory,
    register_artifact,
    safe_save_upload,
)
from src.db import db_execute_one, get_connection

router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/upload/{case_id}/{kind}")
def upload(case_id: str, kind: str, file: UploadFile = File(...)):
    """Upload document for a case (DAO, offer, template)."""
    with get_connection() as conn:
        c = db_execute_one(conn, "SELECT id FROM cases WHERE id=:id", {"id": case_id})
    if not c:
        raise HTTPException(status_code=404, detail="case not found")

    kind = kind.strip().lower()
    allowed = {"dao", "offer", "cba_template", "pv_template"}
    if kind not in allowed:
        raise HTTPException(
            status_code=400, detail=f"kind must be one of {sorted(list(allowed))}"
        )

    filename, path = safe_save_upload(case_id, kind, file)
    aid = register_artifact(
        case_id, kind, filename, path, meta={"original_name": file.filename}
    )

    return {"ok": True, "artifact_id": aid, "filename": filename}


@router.get("/download/{case_id}/{kind}")
def download_latest(case_id: str, kind: str):
    """Download latest generated artifact"""
    kind = kind.strip().lower()
    if kind not in {"output_cba", "output_pv"}:
        raise HTTPException(
            status_code=400, detail="kind must be output_cba or output_pv"
        )

    arts = get_artifacts(case_id, kind)
    if not arts:
        raise HTTPException(status_code=404, detail=f"No artifact found for {kind}")

    p = Path(arts[0]["path"])
    if not p.exists():
        raise HTTPException(status_code=404, detail="file missing on disk")

    return FileResponse(
        path=str(p), filename=p.name, media_type="application/octet-stream"
    )


@router.get("/memory/{case_id}")
def memory(case_id: str):
    """Retrieve all memory entries for a case"""
    return {"case_id": case_id, "memory": list_memory(case_id)}


@router.get("/search_memory/{case_id}")
def search_memory(case_id: str, q: str):
    """Search memory entries by keyword"""
    q = (q or "").strip().lower()
    if not q:
        return {"case_id": case_id, "hits": []}

    mem = list_memory(case_id)
    hits = []
    for entry in mem:
        blob = json.dumps(entry.get("content", {}), ensure_ascii=False).lower()
        if q in blob:
            hits.append(
                {
                    "id": entry["id"],
                    "entry_type": entry["entry_type"],
                    "created_at": entry["created_at"],
                    "preview": entry["content"],
                }
            )

    return {"case_id": case_id, "q": q, "hits": hits}
