"""W1 — POST commentaires CDE (Canon V5.1.0 O8), monté sous /api/workspaces.

Évite d'alourdir workspaces.py (>800 lignes) — inclusion via APIRouter.include_router.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.workspace_access import require_workspace_comment_permission
from src.db import db_execute_one, get_connection
from src.services.comments_service import add_smart_comment

comments_subrouter = APIRouter()


class WorkspaceCommentCreate(BaseModel):
    """Payload POST /api/workspaces/{workspace_id}/comments."""

    model_config = {"extra": "forbid"}

    content: str = Field(..., min_length=1)
    is_flag: bool = False
    criterion_assessment_id: str | None = None
    criterion_id: str | None = Field(
        None,
        description="Clé critère M16 (criterion_key) ou id dao_criterion — résolu avec supplier_id",
    )
    supplier_id: str | None = Field(
        None,
        description="UUID bundle (supplier_bundles.id) pour résoudre criterion_assessments",
    )

    @model_validator(mode="after")
    def _pair_or_direct(self) -> WorkspaceCommentCreate:
        has_ca = bool(self.criterion_assessment_id)
        has_pair = bool(self.criterion_id and self.supplier_id)
        if has_ca and has_pair:
            raise ValueError(
                "Fournir soit criterion_assessment_id, soit (criterion_id + supplier_id), pas les deux."
            )
        if (self.criterion_id and not self.supplier_id) or (
            self.supplier_id and not self.criterion_id
        ):
            raise ValueError(
                "criterion_id et supplier_id doivent être fournis ensemble pour une cellule."
            )
        return self


def _resolve_criterion_assessment_id(
    conn: object,
    *,
    workspace_id: str,
    tenant_id: str,
    criterion_id: str,
    supplier_id: str,
) -> str | None:
    """Résout criterion_assessments.id depuis bundle + clé critère."""
    row = db_execute_one(
        conn,
        """
        SELECT ca.id::text AS id
        FROM criterion_assessments ca
        JOIN supplier_bundles sb ON sb.id = ca.bundle_id
        WHERE ca.workspace_id = CAST(:ws AS uuid)
          AND ca.tenant_id = CAST(:tid AS uuid)
          AND ca.bundle_id = CAST(:bid AS uuid)
          AND (
              ca.criterion_key = :ckey
              OR CAST(ca.dao_criterion_id AS text) = :ckey
          )
        LIMIT 1
        """,
        {
            "ws": workspace_id,
            "tid": tenant_id,
            "bid": supplier_id,
            "ckey": criterion_id,
        },
    )
    return str(row["id"]) if row and row.get("id") else None


def _verify_assessment_in_workspace(
    conn: object,
    *,
    workspace_id: str,
    tenant_id: str,
    criterion_assessment_id: str,
) -> bool:
    row = db_execute_one(
        conn,
        """
        SELECT id FROM criterion_assessments
        WHERE id = CAST(:caid AS uuid)
          AND workspace_id = CAST(:ws AS uuid)
          AND tenant_id = CAST(:tid AS uuid)
        LIMIT 1
        """,
        {"caid": criterion_assessment_id, "ws": workspace_id, "tid": tenant_id},
    )
    return row is not None


@comments_subrouter.post("/{workspace_id}/comments")
def post_workspace_comment(
    workspace_id: str,
    payload: WorkspaceCommentCreate,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Crée un commentaire / flag CDE (deliberation_messages + assessment_comments)."""
    require_workspace_comment_permission(workspace_id, user)

    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )
    tenant_s = str(tenant_id)
    author_user_id = int(user.user_id)

    criterion_assessment_id: str | None = payload.criterion_assessment_id

    with get_connection() as conn:
        ws = db_execute_one(
            conn,
            "SELECT id, tenant_id FROM process_workspaces WHERE id = :id",
            {"id": workspace_id},
        )
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        if str(ws.get("tenant_id") or "") != tenant_s:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workspace hors tenant courant.",
            )

        if payload.criterion_id and payload.supplier_id:
            criterion_assessment_id = _resolve_criterion_assessment_id(
                conn,
                workspace_id=workspace_id,
                tenant_id=tenant_s,
                criterion_id=payload.criterion_id,
                supplier_id=payload.supplier_id,
            )
            if not criterion_assessment_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cellule critère × fournisseur introuvable pour ce workspace.",
                )

        if criterion_assessment_id and not _verify_assessment_in_workspace(
            conn,
            workspace_id=workspace_id,
            tenant_id=tenant_s,
            criterion_assessment_id=criterion_assessment_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="criterion_assessment_id inconnu pour ce workspace.",
            )

        try:
            result = add_smart_comment(
                conn,
                workspace_id=workspace_id,
                tenant_id=tenant_s,
                author_user_id=author_user_id,
                content=payload.content,
                is_flag=payload.is_flag,
                criterion_assessment_id=criterion_assessment_id,
                thread_id=None,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    return result
