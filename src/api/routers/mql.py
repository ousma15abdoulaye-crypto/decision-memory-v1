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
from src.db.async_pool import AsyncpgAdapter, acquire_with_rls

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
    role_perms = ROLE_PERMISSIONS.get(current_user.role or "", frozenset())
    if "mql.internal" not in role_perms and "system.admin" not in role_perms:
        raise HTTPException(403, "Permission mql.internal requise")

    if not current_user.tenant_id:
        raise HTTPException(400, "tenant_id manquant dans le JWT.")

    from src.mql.engine import execute_mql_query

    tenant_id = UUID(str(current_user.tenant_id))
    uid = int(current_user.user_id)
    async with acquire_with_rls(
        str(tenant_id),
        is_admin=(current_user.role == "admin"),
    ) as raw_conn:
        conn = AsyncpgAdapter(raw_conn)
        result = await execute_mql_query(
            db=conn,
            tenant_id=tenant_id,
            workspace_id=payload.workspace_id,
            query=payload.query,
            context=None,
        )
        await raw_conn.execute(
            """
            INSERT INTO mql_query_log
              (tenant_id, workspace_id, user_id, query_text,
               intent_classified, intent_confidence,
               template_used, sources_count, latency_ms,
               model_used, langfuse_trace_id)
            VALUES
              ($1::uuid, $2::uuid, $3, $4,
               'mql_internal', $5,
               $6, $7, $8,
               'mql.internal', NULL)
            """,
            str(tenant_id),
            str(payload.workspace_id) if payload.workspace_id else None,
            uid,
            payload.query,
            float(result.confidence),
            result.template_used,
            len(result.sources),
            result.latency_ms,
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
                "published_date": (
                    s.published_date.isoformat() if s.published_date else None
                ),
                "is_official": s.is_official,
            }
            for s in result.sources
        ],
        "confidence": result.confidence,
        "latency_ms": result.latency_ms,
    }
