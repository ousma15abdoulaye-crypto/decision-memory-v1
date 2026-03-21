"""Case-level access control (owner + admin bypass).

Used by API routes that take case_id but are outside couche_a.routers upload paths.
Does not replace DB RLS; blocks obvious IDOR at the application layer.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from src.couche_a.auth.dependencies import UserClaims
from src.db import db_execute_one, get_connection
from src.extraction.engine import get_document


def require_case_access(case_id: str, user: UserClaims) -> None:
    """Raise 404 if case missing; 403 if non-admin and not owner."""
    with get_connection() as conn:
        row = db_execute_one(
            conn,
            "SELECT owner_id FROM cases WHERE id = :id",
            {"id": case_id},
        )
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    if user.role == "admin":
        return

    owner_id = row.get("owner_id")
    if owner_id is None or int(owner_id) != int(user.user_id):
        raise HTTPException(status_code=403, detail="You do not own this case")


def require_document_case_access(document_id: str, user: UserClaims) -> dict[str, Any]:
    """Load document, enforce case ownership (or admin). Returns document row dict."""
    try:
        doc = get_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    case_id = doc.get("case_id")
    if not case_id:
        raise HTTPException(status_code=404, detail="Document has no associated case")

    require_case_access(str(case_id), user)
    return doc


def require_case_tenant_org(case_id: str, org_id: str, user: UserClaims) -> None:
    """Vérifie accès au case et que org_id client == cases.tenant_id (anti-IDOR R7)."""
    require_case_access(case_id, user)
    with get_connection() as conn:
        row = db_execute_one(
            conn,
            "SELECT tenant_id FROM cases WHERE id = :id",
            {"id": case_id},
        )
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    if row.get("tenant_id") != org_id:
        raise HTTPException(
            status_code=422,
            detail="org_id ne correspond pas au tenant du dossier",
        )
