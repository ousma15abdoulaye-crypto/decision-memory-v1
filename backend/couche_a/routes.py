"""Couche A – FastAPI routes for procurement case management."""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.couche_a.models import (
    CBAExport,
    MinutesPV,
    PreanalysisResult,
    Submission,
    SubmissionDocument,
)
from backend.system.audit import log_audit
from backend.system.auth import UserPayload, get_current_user
from backend.system.db import get_db
from backend.system.settings import get_settings

__all__ = ["router"]

router = APIRouter(tags=["couche_a"])


def _sanitize_path_component(value: str) -> str:
    """Remove path traversal characters from user-provided path components."""
    return re.sub(r"[^a-zA-Z0-9_\-.]", "_", value)


# ---- POST /api/depot --------------------------------------------------------

@router.post("/api/depot", status_code=status.HTTP_201_CREATED)
async def depot_upload(
    case_id: Annotated[str, Form()],
    lot_id: Annotated[str, Form()],
    channel: Annotated[str, Form()] = "upload",
    declared_type: Annotated[str | None, Form()] = None,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(get_current_user),
):
    settings = get_settings()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="File exceeds maximum size")

    # Ensure upload dir exists
    upload_dir = os.path.join(
        settings.UPLOAD_DIR,
        _sanitize_path_component(case_id),
        _sanitize_path_component(lot_id),
    )
    os.makedirs(upload_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    safe_name = f"{file_id}_{_sanitize_path_component(file.filename or 'unknown')}"
    file_path = os.path.join(upload_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    file_hash = hashlib.sha256(content).hexdigest()

    # Create submission
    submission = Submission(
        case_id=case_id,
        lot_id=lot_id,
        vendor_name="TBD",
        declared_type=declared_type,
        channel=channel,
    )
    db.add(submission)
    await db.flush()

    doc = SubmissionDocument(
        submission_id=submission.id,
        filename=file.filename or "unknown",
        file_path=file_path,
        file_hash=file_hash,
        file_size=len(content),
        doc_type=declared_type,
    )
    db.add(doc)
    await db.flush()

    await log_audit(db, user.id, "depot_upload", "submission", submission.id, {"filename": file.filename})

    # Trigger extraction (inline for small files, celery for large)
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.CELERY_THRESHOLD_MB:
        from backend.workers.tasks import extract_document_task
        extract_document_task.delay(doc.id, file_path)
    else:
        from backend.couche_a.analyzer import run_extraction
        await run_extraction(doc.id, file_path, db)

    return {"submission_id": submission.id, "document_id": doc.id, "status": "received"}


# ---- GET /api/dashboard -----------------------------------------------------

@router.get("/api/dashboard")
async def dashboard(
    case_id: str = Query(default=None),
    lot_id: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(get_current_user),
):
    stmt = select(Submission)
    if case_id:
        stmt = stmt.where(Submission.case_id == case_id)
    if lot_id:
        stmt = stmt.where(Submission.lot_id == lot_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(stmt)).scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "id": s.id,
                "case_id": s.case_id,
                "lot_id": s.lot_id,
                "vendor_name": s.vendor_name,
                "status": s.status,
                "channel": s.channel,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in rows
        ],
    }


# ---- GET /api/offers/{submission_id} ----------------------------------------

@router.get("/api/offers/{submission_id}")
async def get_offer(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(get_current_user),
):
    stmt = select(Submission).where(Submission.id == submission_id)
    sub = (await db.execute(stmt)).scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    pre_stmt = select(PreanalysisResult).where(PreanalysisResult.submission_id == submission_id)
    preanalysis = (await db.execute(pre_stmt)).scalars().all()

    return {
        "submission": {
            "id": sub.id,
            "case_id": sub.case_id,
            "lot_id": sub.lot_id,
            "vendor_name": sub.vendor_name,
            "status": sub.status,
            "channel": sub.channel,
        },
        "preanalysis": [
            {
                "id": p.id,
                "vendor_name": p.vendor_name,
                "amount": p.amount,
                "detected_type": p.detected_type,
                "doc_checklist": p.doc_checklist,
                "flags": p.flags,
                "llm_used": p.llm_used,
            }
            for p in preanalysis
        ],
    }


# ---- POST /api/export-cba ---------------------------------------------------

@router.post("/api/export-cba")
async def export_cba(
    case_id: str = Query(...),
    lot_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(get_current_user),
):
    from backend.couche_a.cba_export import generate_cba_excel

    file_path = await generate_cba_excel(case_id, lot_id, db)

    export = CBAExport(
        case_id=case_id, lot_id=lot_id, file_path=file_path, created_by=user.id
    )
    db.add(export)
    await db.flush()

    await log_audit(db, user.id, "export_cba", "cba_export", export.id)
    return {"export_id": export.id, "file_path": file_path}


# ---- POST /api/cba-review/upload --------------------------------------------

@router.post("/api/cba-review/upload")
async def cba_review_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(get_current_user),
):
    settings = get_settings()
    content = await file.read()

    upload_dir = os.path.join(settings.UPLOAD_DIR, "cba_reviews")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{_sanitize_path_component(file.filename or 'unknown')}")
    with open(file_path, "wb") as f:
        f.write(content)

    from backend.couche_a.cba_export import parse_revised_cba

    revisions = parse_revised_cba(file_path)
    await log_audit(db, user.id, "cba_review_upload", "cba_review", "", {"revisions_count": len(revisions)})
    return {"file_path": file_path, "revisions": revisions}


# ---- POST /api/pv/opening ---------------------------------------------------

@router.post("/api/pv/opening")
async def pv_opening(
    case_id: str = Query(...),
    lot_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(get_current_user),
):
    from backend.couche_a.pv_generator import generate_pv_opening

    file_path = await generate_pv_opening(case_id, lot_id, db)

    pv = MinutesPV(
        case_id=case_id, lot_id=lot_id, pv_type="opening", file_path=file_path, created_by=user.id
    )
    db.add(pv)
    await db.flush()
    await log_audit(db, user.id, "pv_opening", "minutes_pv", pv.id)
    return {"pv_id": pv.id, "file_path": file_path}


# ---- POST /api/pv/analysis --------------------------------------------------

@router.post("/api/pv/analysis")
async def pv_analysis(
    case_id: str = Query(...),
    lot_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(get_current_user),
):
    from backend.couche_a.pv_generator import generate_pv_analysis

    file_path = await generate_pv_analysis(case_id, lot_id, db)

    pv = MinutesPV(
        case_id=case_id, lot_id=lot_id, pv_type="analysis", file_path=file_path, created_by=user.id
    )
    db.add(pv)
    await db.flush()
    await log_audit(db, user.id, "pv_analysis", "minutes_pv", pv.id)
    return {"pv_id": pv.id, "file_path": file_path}
