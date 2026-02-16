"""
Case management endpoints.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from src.db import get_connection, db_execute, db_execute_one, db_fetchall
from src.core.models import CaseCreate
from src.core.dependencies import get_artifacts, list_memory
from src.auth import CurrentUser
from src.ratelimit import limiter

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("")
@limiter.limit("10/minute")
async def create_case(request: Request, payload: CaseCreate, user: CurrentUser):
    """Crée nouveau case (requiert authentification)."""
    case_type = payload.case_type.strip().upper()
    if case_type not in {"DAO", "RFQ"}:
        raise HTTPException(status_code=400, detail="case_type must be DAO or RFQ")

    case_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        db_execute(
            conn,
            """
            INSERT INTO cases (id, case_type, title, lot, created_at, status, owner_id)
            VALUES (:id, :ctype, :title, :lot, :ts, :status, :owner)
        """,
            {
                "id": case_id,
                "ctype": case_type,
                "title": payload.title.strip(),
                "lot": payload.lot,
                "ts": now,
                "status": "open",
                "owner": user["id"],
            },
        )

    return {
        "id": case_id,
        "case_type": case_type,
        "title": payload.title,
        "lot": payload.lot,
        "created_at": now,
        "status": "open",
        "owner_id": user["id"],
    }


@router.get("")
@limiter.limit("50/minute")
def list_cases(request: Request):
    """Liste tous les cases (rate limited)."""
    with get_connection() as conn:
        rows = db_fetchall(conn, "SELECT * FROM cases ORDER BY created_at DESC")
    return rows


@router.get("/{case_id}")
def get_case(case_id: str):
    with get_connection() as conn:
        c = db_execute_one(conn, "SELECT * FROM cases WHERE id=:id", {"id": case_id})
    if not c:
        raise HTTPException(status_code=404, detail="case not found")

    arts = get_artifacts(case_id)
    mem = list_memory(case_id)

    # Get DAO criteria if analyzed
    with get_connection() as conn:
        criteria = db_fetchall(
            conn,
            "SELECT * FROM dao_criteria WHERE case_id=:cid ORDER BY ordre_affichage",
            {"cid": case_id},
        )

    return {"case": dict(c), "artifacts": arts, "memory": mem, "dao_criteria": criteria}
