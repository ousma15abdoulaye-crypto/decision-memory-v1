"""O4 — Membres workspace : liste, invitation nominative, révocation tracée."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from pydantic import BaseModel, Field

from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.workspace_access import require_workspace_permission
from src.db import db_execute, db_execute_one, db_fetchall, get_connection
from src.services.workspace_access_service import WorkspaceRole

router = APIRouter(prefix="/api/workspaces", tags=["workspace-members-v51"])

_VALID_ROLES = frozenset(m.value for m in WorkspaceRole)


class WorkspaceMemberInvite(BaseModel):
    model_config = {"extra": "forbid"}

    user_id: int = Field(..., ge=1)
    role: str = Field(..., min_length=1)


@router.get("/{workspace_id}/members")
def list_workspace_members(
    workspace_id: str,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    require_workspace_permission(workspace_id, user, "matrix.read")
    tid = user.tenant_id
    if not tid:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )
    with get_connection() as conn:
        rows = db_fetchall(
            conn,
            """
            SELECT wm.id, wm.user_id, wm.role, wm.granted_at, wm.revoked_at,
                   wm.coi_declared, wm.coi_declared_at, wm.granted_by
            FROM workspace_memberships wm
            JOIN process_workspaces w ON w.id = wm.workspace_id
            WHERE wm.workspace_id = CAST(:ws AS uuid)
              AND w.tenant_id = CAST(:tid AS uuid)
            ORDER BY wm.granted_at ASC
            """,
            {"ws": workspace_id, "tid": str(tid)},
        )
    return {"workspace_id": workspace_id, "members": rows}


@router.post("/{workspace_id}/members", status_code=http_status.HTTP_201_CREATED)
def invite_workspace_member(
    workspace_id: str,
    payload: WorkspaceMemberInvite,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    require_workspace_permission(workspace_id, user, "member.invite")
    if payload.role not in _VALID_ROLES:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role invalide. Valeurs : {sorted(_VALID_ROLES)}",
        )
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )
    actor_id = int(user.user_id)
    with get_connection() as conn:
        ws = db_execute_one(
            conn,
            "SELECT id, tenant_id FROM process_workspaces WHERE id = CAST(:id AS uuid)",
            {"id": workspace_id},
        )
        if not ws:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)
        ws_tid = str(ws["tenant_id"])
        target = db_execute_one(
            conn,
            "SELECT id FROM users WHERE id = :uid",
            {"uid": payload.user_id},
        )
        if not target:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Utilisateur cible introuvable.",
            )
        existing = db_execute_one(
            conn,
            """
            SELECT id, revoked_at FROM workspace_memberships
            WHERE workspace_id = CAST(:ws AS uuid)
              AND user_id = :uid AND role = :role
            """,
            {"ws": workspace_id, "uid": payload.user_id, "role": payload.role},
        )
        if existing and existing.get("revoked_at") is None:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Membership déjà actif pour ce rôle.",
            )
        db_execute(
            conn,
            """
            INSERT INTO workspace_memberships (
                workspace_id, tenant_id, user_id, role, granted_by
            )
            VALUES (
                CAST(:ws AS uuid),
                CAST(:tid AS uuid),
                :uid,
                :role,
                :granted_by
            )
            ON CONFLICT (workspace_id, user_id, role) DO UPDATE SET
                revoked_at = NULL,
                granted_by = EXCLUDED.granted_by,
                granted_at = NOW()
            """,
            {
                "ws": workspace_id,
                "tid": ws_tid,
                "uid": payload.user_id,
                "role": payload.role,
                "granted_by": actor_id,
            },
        )
        db_execute(
            conn,
            """
            INSERT INTO workspace_events
                (workspace_id, tenant_id, event_type, actor_id, actor_type, payload)
            VALUES
                (CAST(:ws AS uuid), CAST(:tid AS uuid), 'MEMBER_INVITED', :actor, 'user', :p)
            """,
            {
                "ws": workspace_id,
                "tid": ws_tid,
                "actor": actor_id,
                "p": json.dumps(
                    {"user_id": payload.user_id, "role": payload.role},
                    ensure_ascii=False,
                ),
            },
        )
    return {"status": "invited", "user_id": payload.user_id, "role": payload.role}


@router.delete(
    "/{workspace_id}/members/{member_user_id}", status_code=http_status.HTTP_200_OK
)
def revoke_workspace_member(
    workspace_id: str,
    member_user_id: int,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    require_workspace_permission(workspace_id, user, "member.revoke")
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )
    actor_id = int(user.user_id)
    if member_user_id == actor_id:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Révocation de soi-même interdite.",
        )
    now = datetime.now(UTC)
    with get_connection() as conn:
        n = db_execute_one(
            conn,
            """
            UPDATE workspace_memberships AS wm
            SET revoked_at = :now
            FROM process_workspaces AS w
            WHERE wm.workspace_id = w.id
              AND w.id = CAST(:ws AS uuid)
              AND w.tenant_id = CAST(:tid AS uuid)
              AND wm.user_id = :uid
              AND wm.revoked_at IS NULL
            RETURNING wm.id
            """,
            {
                "ws": workspace_id,
                "tid": str(tenant_id),
                "uid": member_user_id,
                "now": now,
            },
        )
        if not n:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Aucun membership actif pour cet utilisateur.",
            )
        db_execute(
            conn,
            """
            INSERT INTO workspace_events
                (workspace_id, tenant_id, event_type, actor_id, actor_type, payload)
            VALUES
                (CAST(:ws AS uuid), CAST(:tid AS uuid), 'MEMBER_REVOKED', :actor, 'user', :p)
            """,
            {
                "ws": workspace_id,
                "tid": str(tenant_id),
                "actor": actor_id,
                "p": json.dumps({"user_id": member_user_id}, ensure_ascii=False),
            },
        )
    return {"status": "revoked", "user_id": member_user_id}
