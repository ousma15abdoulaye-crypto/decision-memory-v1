"""Routes W3 — Committee Sessions (V4.2.0).

Routes implémentées :
  GET  /api/workspaces/{id}/committee               : détail session comité
  POST /api/workspaces/{id}/committee/open-session  : ouvrir session
  POST /api/workspaces/{id}/committee/add-member    : ajouter membre
  POST /api/workspaces/{id}/committee/seal          : sceller la session (IRR)

Non implémentés (chantier futur) :
  POST /api/workspaces/{id}/committee/add-comment
  POST /api/workspaces/{id}/committee/challenge-score

Référence : docs/freeze/DMS_V4.2.0_ADDENDUM.md §VII routes W3
INV-W01 : actes irréversibles — committee_deliberation_events append-only.
INV-W04 : session sealed → aucune transition vers draft/active.
INV-W06 : aucun champ winner/rank dans les réponses.
RÈGLE-W01 : le contexte locataire pour l’autorisation (JWT, accès workspace) reste la
référence RBAC. Pour les écritures CDE (`committee_deliberation_events.tenant_id`),
la valeur doit correspondre à la ligne métier : `committee_sessions.tenant_id`, avec
repli `process_workspaces.tenant_id` si la session n’a pas de tenant — jamais une
chaîne vide ou une valeur inventée pour compenser des claims JWT incomplets.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi import status as http_status
from pydantic import BaseModel

from src.api.cognitive_helpers import load_cognitive_facts
from src.cognitive.cognitive_state import TransitionForbidden, validate_transition
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.workspace_access import (
    require_workspace_access,
    require_workspace_permission,
)
from src.db import db_execute, db_execute_one, get_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workspaces", tags=["committee-v420"])


def _tenant_id_for_cde_writes(conn, workspace_id: str, user: UserClaims) -> str:
    """UUID tenant pour écritures CDE : JWT d’abord, sinon `process_workspaces`."""
    if user.tenant_id:
        return str(user.tenant_id)
    ws = db_execute_one(
        conn,
        "SELECT tenant_id FROM process_workspaces WHERE id = :wid",
        {"wid": workspace_id},
    )
    if ws and ws.get("tenant_id"):
        return str(ws["tenant_id"])
    raise HTTPException(
        status_code=http_status.HTTP_400_BAD_REQUEST,
        detail="tenant_id introuvable (JWT ou workspace).",
    )


async def _enqueue_project_sealed_workspace_job(workspace_id: str) -> None:
    """Enqueue BLOC5 ARQ projection (après COMMIT — appelé via BackgroundTasks)."""

    pool = None
    try:
        import arq  # type: ignore[import-untyped]

        redis_url = os.environ.get("REDIS_URL", "").strip()
        if not redis_url:
            logger.warning(
                "[W3] REDIS_URL absent — project_sealed_workspace non enqueue"
            )
            return
        pool = await arq.create_pool(arq.connections.RedisSettings.from_dsn(redis_url))
        await pool.enqueue_job("project_sealed_workspace", workspace_id=workspace_id)
        logger.info("[W3] project_sealed_workspace enqueue workspace=%s", workspace_id)
    except Exception as exc:
        logger.warning("[W3] enqueue project_sealed_workspace: %s", exc)
    finally:
        if pool is not None:
            await pool.close()


@router.get("/{workspace_id}/committee")
def get_committee_session(
    workspace_id: str,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Retourne la session comité du workspace (1 session max par workspace)."""
    require_workspace_access(workspace_id, user)

    with get_connection() as conn:
        session = db_execute_one(
            conn,
            """
            SELECT id, workspace_id, committee_type, session_status,
                   min_members, activated_at, deliberation_opened_at,
                   sealed_at, closed_at, seal_hash
            FROM committee_sessions
            WHERE workspace_id = :ws
            """,
            {"ws": workspace_id},
        )

    if not session:
        return {"workspace_id": workspace_id, "session": None}

    return {"workspace_id": workspace_id, "session": session}


class OpenSessionPayload(BaseModel):
    model_config = {"extra": "forbid"}

    committee_type: str = "standard"
    min_members: int = 3


@router.post(
    "/{workspace_id}/committee/open-session", status_code=http_status.HTTP_201_CREATED
)
def open_committee_session(
    workspace_id: str,
    payload: OpenSessionPayload,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Crée et active la session comité pour ce workspace."""
    require_workspace_permission(workspace_id, user, "committee.manage")

    if payload.committee_type not in {"standard", "humanitarian", "simplified"}:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="committee_type invalide.",
        )

    user_id = int(user.user_id)

    with get_connection() as conn:
        tenant_id = _tenant_id_for_cde_writes(conn, workspace_id, user)
        existing = db_execute_one(
            conn,
            "SELECT id, session_status FROM committee_sessions WHERE workspace_id = :ws",
            {"ws": workspace_id},
        )
        if existing:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=(
                    f"Session comité déjà existante "
                    f"(status={existing['session_status']})."
                ),
            )

        session_id = str(uuid.uuid4())
        db_execute(
            conn,
            """
            INSERT INTO committee_sessions
                (id, workspace_id, tenant_id, committee_type, min_members,
                 session_status, activated_at)
            VALUES (:id, :ws, :tid, :ctype, :min, 'active', NOW())
            """,
            {
                "id": session_id,
                "ws": workspace_id,
                "tid": tenant_id,
                "ctype": payload.committee_type,
                "min": payload.min_members,
            },
        )

        db_execute(
            conn,
            """
            INSERT INTO committee_deliberation_events
                (session_id, workspace_id, tenant_id, actor_id, event_type, payload)
            VALUES (:sid, :ws, :tid, :uid, 'session_activated', :p)
            """,
            {
                "sid": session_id,
                "ws": workspace_id,
                "tid": tenant_id,
                "uid": user_id,
                "p": json.dumps({"committee_type": payload.committee_type}),
            },
        )

    return {"session_id": session_id, "status": "active"}


class AddMemberPayload(BaseModel):
    model_config = {"extra": "forbid"}

    user_id: int
    role_in_committee: str
    is_voting: bool = True


@router.post("/{workspace_id}/committee/add-member")
def add_committee_member(
    workspace_id: str,
    payload: AddMemberPayload,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Ajoute un membre à la session comité."""
    require_workspace_permission(workspace_id, user, "committee.manage")

    valid_roles = {
        "supply_chain",
        "finance",
        "budget_holder",
        "technical",
        "security",
        "pharma",
        "observer",
        "secretary",
    }
    if payload.role_in_committee not in valid_roles:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role_in_committee invalide. Valeurs : {sorted(valid_roles)}",
        )

    actor_id = int(user.user_id)

    with get_connection() as conn:
        tenant_id = _tenant_id_for_cde_writes(conn, workspace_id, user)
        session = db_execute_one(
            conn,
            "SELECT id, session_status FROM committee_sessions WHERE workspace_id = :ws",
            {"ws": workspace_id},
        )
        if not session:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Session non trouvée.",
            )
        if session["session_status"] in {"sealed", "closed"}:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Session scellée — impossible d'ajouter un membre.",
            )

        member_id = str(uuid.uuid4())
        db_execute(
            conn,
            """
            INSERT INTO committee_session_members
                (id, session_id, workspace_id, tenant_id, user_id,
                 role_in_committee, is_voting)
            VALUES (:id, :sid, :ws, :tid, :uid, :role, :voting)
            ON CONFLICT (session_id, user_id) DO NOTHING
            """,
            {
                "id": member_id,
                "sid": session["id"],
                "ws": workspace_id,
                "tid": tenant_id,
                "uid": payload.user_id,
                "role": payload.role_in_committee,
                "voting": payload.is_voting,
            },
        )

        db_execute(
            conn,
            """
            INSERT INTO committee_deliberation_events
                (session_id, workspace_id, tenant_id, actor_id, event_type, payload)
            VALUES (:sid, :ws, :tid, :actor, 'member_added', :p)
            """,
            {
                "sid": session["id"],
                "ws": workspace_id,
                "tid": tenant_id,
                "actor": actor_id,
                "p": json.dumps(
                    {"user_id": payload.user_id, "role": payload.role_in_committee}
                ),
            },
        )

    return {"status": "member_added", "user_id": payload.user_id}


class SealSessionPayload(BaseModel):
    model_config = {"extra": "forbid"}

    seal_comment: str | None = None


@router.post("/{workspace_id}/committee/seal")
def seal_committee_session(
    workspace_id: str,
    payload: SealSessionPayload,
    background_tasks: BackgroundTasks,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Scelle la session comité (IRR — INV-W01, INV-W04).

    Calcule le seal_hash SHA-256 du snapshot PV.
    Après scellement : aucune modification possible.
    """
    require_workspace_permission(workspace_id, user, "committee.manage")

    user_id = int(user.user_id)

    with get_connection() as conn:
        session = db_execute_one(
            conn,
            """
            SELECT id, session_status, tenant_id
            FROM committee_sessions
            WHERE workspace_id = :ws
            """,
            {"ws": workspace_id},
        )
        if not session:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Session non trouvée.",
            )
        if session["session_status"] == "sealed":
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Session déjà scellée.",
            )
        if session["session_status"] == "closed":
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Session clôturée.",
            )

        ws_row = db_execute_one(
            conn,
            "SELECT * FROM process_workspaces WHERE id = :wid",
            {"wid": workspace_id},
        )
        if not ws_row:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Workspace introuvable.",
            )
        if str(ws_row.get("status") or "") != "in_deliberation":
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=(
                    "Le workspace doit être en statut in_deliberation avant le "
                    "scellement IRR (guards BLOC5 — utiliser PATCH …/status)."
                ),
            )
        facts = load_cognitive_facts(conn, ws_row)
        try:
            validate_transition(str(ws_row.get("status") or "draft"), "sealed", facts)
        except TransitionForbidden as exc:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=exc.reason,
            ) from exc

        # Un seul instantané pour le snapshot PV, la colonne `sealed_at` et le hash
        # (évite un décalage hash / ligne DB si `NOW()` ≠ horloge applicative).
        sealed_at = datetime.now(UTC)
        pv_snapshot = {
            "workspace_id": workspace_id,
            "session_id": session["id"],
            "sealed_by": user_id,
            "sealed_at": sealed_at.isoformat(),
            "seal_comment": payload.seal_comment,
        }
        pv_json = json.dumps(pv_snapshot, sort_keys=True)
        seal_hash = hashlib.sha256(pv_json.encode()).hexdigest()

        # CDE.tenant_id : session puis workspace — UUID NOT NULL (pas de chaîne vide).
        raw_tid = session.get("tenant_id")
        if raw_tid is None:
            ws_row = db_execute_one(
                conn,
                "SELECT tenant_id FROM process_workspaces WHERE id = :wid",
                {"wid": workspace_id},
            )
            raw_tid = ws_row["tenant_id"] if ws_row else None
        if not raw_tid:
            logger.error(
                "seal_committee_session: tenant_id introuvable session=%s workspace=%s",
                session["id"],
                workspace_id,
            )
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="tenant_id introuvable pour le journal de délibération",
            )
        tid_cde = str(raw_tid)

        db_execute(
            conn,
            """
            UPDATE committee_sessions
            SET session_status = 'sealed',
                sealed_at = :sealed_at,
                sealed_by = :uid,
                seal_hash = :hash,
                pv_snapshot = :pv
            WHERE id = :sid
            """,
            {
                "sealed_at": sealed_at,
                "uid": user_id,
                "hash": seal_hash,
                "pv": pv_json,
                "sid": session["id"],
            },
        )

        db_execute(
            conn,
            """
            INSERT INTO committee_deliberation_events
                (session_id, workspace_id, tenant_id, actor_id, event_type, payload)
            VALUES (:sid, :ws, :tid, :actor, 'session_sealed', :p)
            """,
            {
                "sid": session["id"],
                "ws": workspace_id,
                "tid": tid_cde,
                "actor": user_id,
                "p": json.dumps({"seal_hash": seal_hash}),
            },
        )

        db_execute(
            conn,
            """
            UPDATE process_workspaces
            SET status = 'sealed',
                sealed_at = :sealed_at
            WHERE id = :wid
            """,
            {"sealed_at": sealed_at, "wid": workspace_id},
        )
        db_execute(
            conn,
            """
            INSERT INTO workspace_events
                (workspace_id, tenant_id, event_type, actor_id, actor_type, payload)
            VALUES (:ws, :tid, 'WORKSPACE_STATUS_CHANGED', :uid, 'user', :p)
            """,
            {
                "ws": workspace_id,
                "tid": tid_cde,
                "uid": user_id,
                "p": json.dumps(
                    {
                        "from": str(ws_row.get("status")),
                        "to": "sealed",
                        "via": "committee_seal",
                    }
                ),
            },
        )

    background_tasks.add_task(_enqueue_project_sealed_workspace_job, workspace_id)

    return {
        "session_id": session["id"],
        "status": "sealed",
        "seal_hash": seal_hash,
    }
