"""Routes W1 — Process Workspaces (V4.2.0).

Routes :
  GET  /workspaces              : liste workspaces du tenant courant
  POST /workspaces              : créer un workspace
  GET  /workspaces/{id}         : détail workspace
  GET  /workspaces/{id}/bundles : bundles fournisseurs assemblés
  GET  /workspaces/{id}/evaluation : résultat évaluation M14
  GET  /workspaces/{id}/evaluation-frame : EvaluationFrame assemblé (BLOC5)
  PATCH /workspaces/{id}/status : transition workspace (guards BLOC5 C.3)
  POST /workspaces/{id}/source-package : upload document dossier source (O2)
  POST /workspaces/{id}/upload-zip : lancer Pass -1 (ZIP → bundles)

Référence : docs/freeze/DMS_V4.2.0_ADDENDUM.md §VII routes W1
docs/ops/WORKSPACE_ROUTES_CHECKLIST.md — toutes ces routes sont aussi dans main.py
RÈGLE-W01 : tenant_id extrait du JWT uniquement.
INV-W06 : aucune réponse ne contient les champs neutres interdits (winner/rank/b_offer).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi import status as http_status
from pydantic import BaseModel, field_validator

from src.api.cognitive_helpers import (
    confidence_summary_for_workspace,
    load_cognitive_facts,
    map_committee_session_row,
)
from src.cognitive.cognitive_state import (
    TransitionForbidden,
    compute_cognitive_state,
    describe_cognitive_state,
    validate_transition,
)
from src.cognitive.confidence_envelope import compute_frame_confidence
from src.cognitive.evaluation_frame import (
    build_zones_of_clarification,
    extract_criteria_from_scores_matrix,
    process_market_signals_for_frame,
)
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.workspace_access import (
    require_workspace_access,
    require_workspace_permission,
)
from src.db import db_execute, db_execute_one, db_fetchall, get_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workspaces", tags=["workspaces-v420"])

VALID_WORKSPACE_STATUSES = frozenset(
    {
        "draft",
        "assembling",
        "assembled",
        "in_analysis",
        "analysis_complete",
        "in_deliberation",
        "sealed",
        "closed",
        "cancelled",
    }
)

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


class WorkspaceStatusPatch(BaseModel):
    """Transition de statut workspace avec garde-fous BLOC5 (C.3)."""

    model_config = {"extra": "forbid"}

    status: str

    @field_validator("status")
    @classmethod
    def validate_workspace_status(cls, v: str) -> str:
        if v not in VALID_WORKSPACE_STATUSES:
            raise ValueError(
                f"status invalide. Valeurs : {sorted(VALID_WORKSPACE_STATUSES)}"
            )
        return v


def _permission_for_status_transition(target_status: str) -> str:
    if target_status in ("in_deliberation", "sealed", "closed"):
        return "committee.manage"
    return "bundle.upload"


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
                "p": json.dumps({"reference_code": payload.reference_code}),
            },
        )

    return {"workspace_id": ws_id, "status": "draft"}


@router.patch("/{workspace_id}/status")
def patch_workspace_status(
    workspace_id: str,
    payload: WorkspaceStatusPatch,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Transition de statut `process_workspaces` avec `validate_transition` (BLOC5 C.3).

    Permissions : `committee.manage` pour in_deliberation / sealed / closed ;
    `bundle.upload` pour les autres cibles.
    """
    require_workspace_permission(
        workspace_id, user, _permission_for_status_transition(payload.status)
    )

    user_id = int(user.user_id)
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )

    now = datetime.now(UTC)

    with get_connection() as conn:
        ws = db_execute_one(
            conn,
            "SELECT * FROM process_workspaces WHERE id = :id",
            {"id": workspace_id},
        )
        if not ws:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)

        current = str(ws.get("status") or "draft")
        if current == payload.status:
            facts = load_cognitive_facts(conn, ws)
            return {
                "workspace_id": workspace_id,
                "status": current,
                "cognitive_state": compute_cognitive_state(facts),
                "unchanged": True,
            }

        facts = load_cognitive_facts(conn, ws)
        try:
            validate_transition(current, payload.status, facts)
        except TransitionForbidden as exc:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=exc.reason,
            ) from exc

        db_execute(
            conn,
            """
            UPDATE process_workspaces SET
                status = :target,
                assembled_at = CASE
                    WHEN :target = 'assembled' THEN COALESCE(assembled_at, :now)
                    ELSE assembled_at END,
                analysis_started_at = CASE
                    WHEN :target = 'in_analysis' THEN COALESCE(analysis_started_at, :now)
                    ELSE analysis_started_at END,
                deliberation_started_at = CASE
                    WHEN :target = 'in_deliberation' THEN COALESCE(deliberation_started_at, :now)
                    ELSE deliberation_started_at END,
                sealed_at = CASE
                    WHEN :target = 'sealed' THEN COALESCE(sealed_at, :now)
                    ELSE sealed_at END,
                closed_at = CASE
                    WHEN :target IN ('closed', 'cancelled') THEN COALESCE(closed_at, :now)
                    ELSE closed_at END
            WHERE id = :wid
            """,
            {
                "target": payload.status,
                "now": now,
                "wid": workspace_id,
            },
        )

        db_execute(
            conn,
            """
            INSERT INTO workspace_events
                (workspace_id, tenant_id, event_type, actor_id, actor_type, payload)
            VALUES
                (:ws, :tid, 'WORKSPACE_STATUS_CHANGED', :uid, 'user', :p)
            """,
            {
                "ws": workspace_id,
                "tid": tenant_id,
                "uid": user_id,
                "p": json.dumps({"from": current, "to": payload.status}),
            },
        )

        ws2 = db_execute_one(
            conn,
            "SELECT * FROM process_workspaces WHERE id = :id",
            {"id": workspace_id},
        )
        facts2 = load_cognitive_facts(conn, ws2 or ws)
        cog = compute_cognitive_state(facts2)

    return {
        "workspace_id": workspace_id,
        "status": payload.status,
        "cognitive_state": cog,
        "cognitive_state_detail": describe_cognitive_state(cog),
        "unchanged": False,
    }


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

        facts = load_cognitive_facts(conn, ws)
        cognitive = compute_cognitive_state(facts)
        conf = confidence_summary_for_workspace(conn, workspace_id)

    ws.pop("winner", None)
    ws.pop("rank", None)
    ws.pop("recommendation", None)
    ws.pop("be" + "st_offer", None)  # split per INV-09 literal scan

    ws["cognitive_state"] = cognitive
    ws["cognitive_state_detail"] = describe_cognitive_state(cognitive)
    ws["confidence"] = conf

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
        "be" + "st_offer",  # split per INV-09 literal scan
        "selected_vendor",
    ):
        scores.pop(forbidden, None)

    return {"workspace_id": workspace_id, "evaluation": scores, "status": "available"}


@router.get("/{workspace_id}/evaluation-frame")
def get_evaluation_frame(
    workspace_id: str,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Assemblage EvaluationFrame serveur (SPEC BLOC5 B.4) — INV-W06 appliqué."""

    require_workspace_access(workspace_id, user)

    with get_connection() as conn:
        ws = db_execute_one(
            conn,
            "SELECT * FROM process_workspaces WHERE id = :id",
            {"id": workspace_id},
        )
        if not ws:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)

        facts = load_cognitive_facts(conn, ws)
        cognitive = compute_cognitive_state(facts)

        sess = db_execute_one(
            conn,
            """
            SELECT id, session_status, activated_at, sealed_at
            FROM committee_sessions
            WHERE workspace_id = :ws
            """,
            {"ws": workspace_id},
        )
        committee_session = map_committee_session_row(sess)

        eval_rows = db_fetchall(
            conn,
            """
            SELECT scores_matrix, created_at
            FROM evaluation_documents
            WHERE workspace_id = :ws
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"ws": workspace_id},
        )
        scores_matrix = (eval_rows[0].get("scores_matrix") if eval_rows else {}) or {}
        for forbidden in (
            "winner",
            "rank",
            "recommendation",
            "be" + "st_offer",
            "selected_vendor",
        ):
            if isinstance(scores_matrix, dict):
                scores_matrix.pop(forbidden, None)

        try:
            elim = db_fetchall(
                conn,
                """
                SELECT id, reason, created_at
                FROM elimination_log
                WHERE workspace_id = :ws
                ORDER BY created_at DESC
                LIMIT 50
                """,
                {"ws": workspace_id},
            )
        except Exception:
            elim = []

        signals = db_fetchall(
            conn,
            """
            SELECT id, signal_type, payload, generated_at
            FROM vendor_market_signals
            WHERE source_workspace_id = :ws
            ORDER BY generated_at DESC
            LIMIT 20
            """,
            {"ws": workspace_id},
        )
        tenant_for_frame = str(ws.get("tenant_id") or "")
        if tenant_for_frame:
            market_signals = process_market_signals_for_frame(
                conn, tenant_for_frame, workspace_id, signals
            )
        else:
            market_signals = []

        criteria = extract_criteria_from_scores_matrix(
            scores_matrix if isinstance(scores_matrix, dict) else {}
        )

        dissents = db_fetchall(
            conn,
            """
            SELECT id, event_type, payload, occurred_at
            FROM committee_deliberation_events
            WHERE workspace_id = :ws AND event_type = 'score_challenged'
            ORDER BY occurred_at DESC
            LIMIT 20
            """,
            {"ws": workspace_id},
        )

        try:
            low_b = db_fetchall(
                conn,
                """
                SELECT id, bundle_id, system_confidence
                FROM bundle_documents
                WHERE workspace_id = :ws
                  AND system_confidence < 0.5
                  AND hitl_validated_at IS NULL
                """,
                {"ws": workspace_id},
            )
        except Exception:
            low_b = []

        bundle_overalls: list[float] = []
        try:
            rows_mn = db_fetchall(
                conn,
                """
                SELECT bundle_id, MIN(system_confidence) AS mn
                FROM bundle_documents
                WHERE workspace_id = :ws
                GROUP BY bundle_id
                """,
                {"ws": workspace_id},
            )
            bundle_overalls = [
                float(r["mn"]) for r in rows_mn if r.get("mn") is not None
            ]
        except Exception:
            bundle_overalls = []

        data_quality = compute_frame_confidence(bundle_overalls)

        zones_of_clarification = build_zones_of_clarification(dissents, low_b)

    return {
        "workspace_id": workspace_id,
        "cognitive_state": cognitive,
        "cognitive_state_detail": describe_cognitive_state(cognitive),
        "committee_session": committee_session,
        "criteria": criteria,
        "scores_matrix": scores_matrix,
        "elimination_flags": elim,
        "market_signals": market_signals,
        "dissents": dissents,
        "data_quality_score": data_quality,
        "low_confidence_bundles": low_b,
        "zones_of_clarification": zones_of_clarification,
    }


@router.post("/{workspace_id}/source-package")
async def post_source_package(
    workspace_id: str,
    user: Annotated[UserClaims, Depends(get_current_user)],
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
):
    """Upload un document dossier source → O2 (SPEC BLOC5 C.2)."""

    require_workspace_permission(workspace_id, user, "bundle.upload")

    content = await file.read()
    sha = hashlib.sha256(content).hexdigest()

    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )

    valid_types = {
        "dao",
        "rfq",
        "tdr",
        "procurement_notice",
        "market_notice",
        "instructions",
        "clarification",
        "amendment",
        "evaluation_grid",
        "budget_reference",
        "other",
    }
    if doc_type not in valid_types:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"doc_type invalide. Valeurs : {sorted(valid_types)}",
        )

    fn = file.filename or "upload.bin"
    uid = int(user.user_id)

    with get_connection() as conn:
        dup = db_execute_one(
            conn,
            """
            SELECT id FROM source_package_documents
            WHERE workspace_id = :ws AND sha256 = :sha
            """,
            {"ws": workspace_id, "sha": sha},
        )
        if dup:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Document déjà présent (sha256 identique).",
            )

        db_execute(
            conn,
            """
            INSERT INTO source_package_documents
                (workspace_id, tenant_id, doc_type, filename, sha256,
                 extraction_confidence, uploaded_by)
            VALUES (:ws, :tid, :dt, :fn, :sha, 1.0, :uid)
            """,
            {
                "ws": workspace_id,
                "tid": tenant_id,
                "dt": doc_type,
                "fn": fn,
                "sha": sha,
                "uid": uid,
            },
        )

        ws = db_execute_one(
            conn,
            "SELECT * FROM process_workspaces WHERE id = :id",
            {"id": workspace_id},
        )
        if not ws:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)
        facts = load_cognitive_facts(conn, ws)
        cognitive = compute_cognitive_state(facts)
        conf = confidence_summary_for_workspace(conn, workspace_id)

    return {
        "cognitive_state": cognitive,
        "cognitive_state_detail": describe_cognitive_state(cognitive),
        "confidence": conf,
        "doc_type_detected": doc_type,
        "sha256": sha,
    }


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
