"""
Case management endpoints.

Règle R7 : chaque case a un tenant_id (colonne DB + claim JWT). Admin : liste globale.
Non-admin : liste filtrée sur tenant_id du token et owner_id (cohérent avec
require_case_access sur GET détail). L’org_id côté API critères = tenant du dossier.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.core.dependencies import get_artifacts, list_memory
from src.core.models import CaseCreate
from src.couche_a.auth.case_access import require_case_access
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.db import db_execute, db_execute_one, db_fetchall, get_connection
from src.ratelimit import limiter

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("")
@limiter.limit("10/minute")
async def create_case(
    request: Request,
    payload: CaseCreate,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Crée nouveau case (requiert authentification)."""
    case_type = payload.case_type.strip().upper()
    if case_type not in {"DAO", "RFQ"}:
        raise HTTPException(status_code=400, detail="case_type must be DAO or RFQ")

    case_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    owner_id = int(user.user_id)
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail="tenant_id manquant pour l'utilisateur — reconnectez-vous après migration",
        )

    with get_connection() as conn:
        db_execute(
            conn,
            """
            INSERT INTO cases (id, case_type, title, lot, created_at, status, owner_id, tenant_id)
            VALUES (:id, :ctype, :title, :lot, :ts, :status, :owner, :tenant)
        """,
            {
                "id": case_id,
                "ctype": case_type,
                "title": payload.title.strip(),
                "lot": payload.lot,
                "ts": now,
                "status": "open",
                "owner": owner_id,
                "tenant": tenant_id,
            },
        )

    return {
        "id": case_id,
        "case_type": case_type,
        "title": payload.title,
        "lot": payload.lot,
        "created_at": now,
        "status": "open",
        "owner_id": owner_id,
        "tenant_id": tenant_id,
    }


@router.get("")
@limiter.limit("50/minute")
def list_cases(
    request: Request,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Liste les cases : admin = tous ; sinon même tenant JWT que l’utilisateur et owner_id = user."""
    with get_connection() as conn:
        if user.role == "admin":
            rows = db_fetchall(conn, "SELECT * FROM cases ORDER BY created_at DESC")
        elif user.tenant_id:
            rows = db_fetchall(
                conn,
                """
                SELECT * FROM cases
                WHERE tenant_id = :tid AND owner_id = :oid
                ORDER BY created_at DESC
                """,
                {"tid": user.tenant_id, "oid": int(user.user_id)},
            )
        else:
            rows = []
    return rows


@router.get("/{case_id}")
def get_case(
    case_id: str,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    require_case_access(case_id, user)

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
