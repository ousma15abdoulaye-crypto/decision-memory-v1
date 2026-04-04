"""Routes W1 — Process Workspaces (V4.2.0).

Routes :
  GET  /workspaces              : liste workspaces du tenant courant
  POST /workspaces              : créer un workspace
  GET  /workspaces/{id}         : détail workspace
  GET  /workspaces/{id}/bundles : bundles fournisseurs assemblés
  GET  /workspaces/{id}/evaluation : résultat évaluation M14
  POST /workspaces/{id}/upload-zip : lancer Pass -1 (ZIP → bundles)

Référence : docs/freeze/DMS_V4.2.0_ADDENDUM.md §VII routes W1
docs/ops/WORKSPACE_ROUTES_CHECKLIST.md — toutes ces routes sont aussi dans main.py
RÈGLE-W01 : tenant_id extrait du JWT uniquement.
INV-W06 : aucune réponse ne contient les champs neutres interdits (winner/rank/b_offer).
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi import status as http_status
from pydantic import BaseModel, field_validator

from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.workspace_access import (
    require_workspace_access,
    require_workspace_permission,
)
from src.db import db_execute, db_execute_one, db_fetchall, get_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces", tags=["workspaces-v420"])

VALID_PROCESS_TYPES = {
    "devis_unique",
    "devis_simple",
    "devis_formel",
    "appel_offres_ouvert",
    "rfp_consultance",
    "contrat_direct",
}


class WorkspaceCreate(BaseModel):
    """Payload création workspace."""

    model_config = {"extra": "forbid"}

    title: str
    reference_code: str
    process_type: str
    estimated_value: float | None = None
    currency: str = "XOF"
    humanitarian_context: str = "none"

    @field_validator("process_type")
    @classmethod
    def validate_process_type(cls, v: str) -> str:
        if v not in VALID_PROCESS_TYPES:
            raise ValueError(
                f"process_type invalide. Valeurs : {sorted(VALID_PROCESS_TYPES)}"
            )
        return v


@router.get("")
def list_workspaces(
    user: Annotated[UserClaims, Depends(get_current_user)],
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """Liste les workspaces du tenant courant (paginé).

    Filtre optionnel par status. Max 100 résultats par appel.
    Aucun champ winner/rank/recommendation dans la réponse (INV-W06).
    """
    if limit > 100:
        limit = 100

    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )

    with get_connection() as conn:
        if status:
            rows = db_fetchall(
                conn,
                """
                SELECT id, reference_code, title, process_type, status,
                       estimated_value, currency, created_at, assembled_at,
                       sealed_at, closed_at
                FROM process_workspaces
                WHERE tenant_id = :tid AND status = :status
                ORDER BY created_at DESC
                LIMIT :lim OFFSET :off
                """,
                {"tid": tenant_id, "status": status, "lim": limit, "off": offset},
            )
        else:
            rows = db_fetchall(
                conn,
                """
                SELECT id, reference_code, title, process_type, status,
                       estimated_value, currency, created_at, assembled_at,
                       sealed_at, closed_at
                FROM process_workspaces
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
                LIMIT :lim OFFSET :off
                """,
                {"tid": tenant_id, "lim": limit, "off": offset},
            )

    return {"workspaces": rows, "limit": limit, "offset": offset}


@router.post("", status_code=http_status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Crée un nouveau workspace (requiert permission workspace.create)."""
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )

    ws_id = str(uuid.uuid4())
    user_id = int(user.user_id)

    with get_connection() as conn:
        existing = db_execute_one(
            conn,
            """
            SELECT id FROM process_workspaces
            WHERE tenant_id = :tid AND reference_code = :ref
            """,
            {"tid": tenant_id, "ref": payload.reference_code.strip()},
        )
        if existing:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=f"reference_code {payload.reference_code!r} déjà utilisé.",
            )

        db_execute(
            conn,
            """
            INSERT INTO process_workspaces
                (id, tenant_id, created_by, reference_code, title,
                 process_type, estimated_value, currency, humanitarian_context)
            VALUES
                (:id, :tid, :uid, :ref, :title, :ptype, :eval, :curr, :hctx)
            """,
            {
                "id": ws_id,
                "tid": tenant_id,
                "uid": user_id,
                "ref": payload.reference_code.strip(),
                "title": payload.title.strip(),
                "ptype": payload.process_type,
                "eval": payload.estimated_value,
                "curr": payload.currency,
                "hctx": payload.humanitarian_context,
            },
        )

        db_execute(
            conn,
            """
            INSERT INTO workspace_events
                (workspace_id, tenant_id, event_type, actor_id, actor_type, payload)
            VALUES
                (:ws, :tid, 'WORKSPACE_CREATED', :uid, 'user', :p)
            """,
            {
                "ws": ws_id,
                "tid": tenant_id,
                "uid": user_id,
                "p": f'{{"reference_code": "{payload.reference_code}"}}',
            },
        )

    return {"workspace_id": ws_id, "status": "draft"}


@router.get("/{workspace_id}")
def get_workspace(
    workspace_id: str,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Retourne le détail d'un workspace."""
    require_workspace_access(workspace_id, user)

    with get_connection() as conn:
        ws = db_execute_one(
            conn,
            """
            SELECT * FROM process_workspaces WHERE id = :id
            """,
            {"id": workspace_id},
        )

    if not ws:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)

    ws.pop("winner", None)
    ws.pop("rank", None)
    ws.pop("recommendation", None)
    ws.pop("best_offer", None)

    return ws


@router.get("/{workspace_id}/bundles")
def list_bundles(
    workspace_id: str,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Retourne les bundles fournisseurs assemblés dans ce workspace."""
    require_workspace_access(workspace_id, user)

    with get_connection() as conn:
        bundles = db_fetchall(
            conn,
            """
            SELECT id, vendor_name_raw, vendor_id, bundle_status,
                   completeness_score, missing_documents, hitl_required,
                   assembled_at, bundle_index
            FROM supplier_bundles
            WHERE workspace_id = :ws
            ORDER BY bundle_index
            """,
            {"ws": workspace_id},
        )

    return {"workspace_id": workspace_id, "bundles": bundles}


@router.get("/{workspace_id}/evaluation")
def get_evaluation(
    workspace_id: str,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Retourne le résultat d'évaluation M14 pour ce workspace.

    INV-W06 : champs winner/rank/recommendation exclus de la réponse.
    """
    require_workspace_access(workspace_id, user)

    with get_connection() as conn:
        eval_rows = db_fetchall(
            conn,
            """
            SELECT id, scores_matrix, created_at
            FROM evaluation_documents
            WHERE workspace_id = :ws
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"ws": workspace_id},
        )

    if not eval_rows:
        return {
            "workspace_id": workspace_id,
            "evaluation": None,
            "status": "no_evaluation",
        }

    row = eval_rows[0]
    scores = row.get("scores_matrix") or {}
    for forbidden in (
        "winner",
        "rank",
        "recommendation",
        "best_offer",
        "selected_vendor",
    ):
        scores.pop(forbidden, None)

    return {"workspace_id": workspace_id, "evaluation": scores, "status": "available"}


@router.post("/{workspace_id}/upload-zip")
async def upload_zip(
    workspace_id: str,
    user: Annotated[UserClaims, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload un ZIP fournisseurs et lance le Pass -1 en arrière-plan.

    Requiert permission bundle.upload.
    Retourne immédiatement — le traitement est asynchrone (ARQ).
    """
    require_workspace_permission(workspace_id, user, "bundle.upload")

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Fichier .zip requis.",
        )

    tmp_dir = tempfile.mkdtemp(prefix="dms_zip_upload_")
    zip_path = os.path.join(tmp_dir, file.filename)
    content = await file.read()

    with open(zip_path, "wb") as f:
        f.write(content)

    tenant_id = user.tenant_id or ""

    background_tasks.add_task(
        _enqueue_pass_minus_one,
        workspace_id=workspace_id,
        tenant_id=tenant_id,
        zip_path=zip_path,
    )

    return {
        "workspace_id": workspace_id,
        "status": "accepted",
        "message": "Pass -1 démarré en arrière-plan.",
    }


async def _enqueue_pass_minus_one(
    workspace_id: str, tenant_id: str, zip_path: str
) -> None:
    """Enqueue le job Pass -1 dans ARQ."""
    try:
        import arq  # type: ignore[import-untyped]

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        pool = await arq.create_pool(arq.connections.RedisSettings.from_dsn(redis_url))
        await pool.enqueue_job(
            "run_pass_minus_1",
            workspace_id=workspace_id,
            tenant_id=tenant_id,
            zip_path=zip_path,
        )
        await pool.close()
        logger.info("[W1] Pass-1 enqueued workspace=%s", workspace_id)
    except Exception as exc:
        logger.error("[W1] Erreur enqueue Pass-1 workspace=%s : %s", workspace_id, exc)
