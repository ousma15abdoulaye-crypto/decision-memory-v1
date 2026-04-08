"""MQL Internal Route — Canon V5.1.0 Section 8.6.

POST /api/mql/stream — route interne admin pour debug et tests.
L'agent utilise le MQL Engine directement (pas cette route).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.auth.permissions import ROLE_PERMISSIONS
from src.couche_a.auth.dependencies import UserClaims, get_current_user

router = APIRouter(prefix="/api", tags=["mql-v51"])


class MQLStreamRequest(BaseModel):
    query: str
    workspace_id: UUID | None = None


@router.post("/mql/stream")
async def mql_stream(
    payload: MQLStreamRequest,
    current_user: UserClaims = Depends(get_current_user),
) -> dict[str, Any]:
    """Route interne MQL. Permission mql.internal (admin uniquement)."""
    role_perms = ROLE_PERMISSIONS.get(current_user.role or "", [])
    if "mql.internal" not in role_perms and "system.admin" not in role_perms:
        raise HTTPException(403, "Permission mql.internal requise")

    from src.mql.engine import execute_mql_query

    result = await execute_mql_query(
        db=None,
        tenant_id=(
            UUID(str(current_user.tenant_id)) if current_user.tenant_id else UUID(int=0)
        ),
        workspace_id=payload.workspace_id,
        query=payload.query,
        context=None,
    )

    return {
        "template_used": result.template_used,
        "row_count": result.row_count,
        "rows": result.rows[:50],
        "sources": [
            {
                "name": s.name,
                "source_type": s.source_type,
                "publisher": s.publisher,
                "is_official": s.is_official,
            }
            for s in result.sources
        ],
        "confidence": result.confidence,
        "latency_ms": result.latency_ms,
    }
