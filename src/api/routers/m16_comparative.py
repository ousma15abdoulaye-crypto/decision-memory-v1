"""Routes M16 — comparatif contradictoire (cadre, backfill, délibération)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.workspace_access import (
    require_workspace_access,
    require_workspace_permission,
)
from src.db import db_execute_one, get_connection
from src.schemas.m16 import (
    CriterionAssessmentOut,
    DeliberationMessageCreate,
    DeliberationMessageOut,
    DeliberationThreadCreate,
    DeliberationThreadOut,
    EvaluationDomainOut,
    M16EvaluationFrameOut,
    M16InitializeResult,
    PriceLineBundleValueOut,
    PriceLineComparisonOut,
    TargetType,
)
from src.services import m16_deliberation_service, m16_evaluation_service
from src.services.comparative_table_model import build_comparative_table_model
from src.services.m16_backfill import initialize_criterion_assessments_from_m14
from src.utils.jinja_filters import build_jinja_env

router = APIRouter(prefix="/api/workspaces", tags=["m16-comparative"])


def _iso(dt: object | None) -> str | None:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


@router.get("/{workspace_id}/m16/comparative-table-model")
def m16_comparative_table_model_json(
    workspace_id: str,
    user: UserClaims = Depends(get_current_user),
):
    """Projection tableau comparatif (live DB), alignée XLSX/PDF — inclut M16 si présent."""
    require_workspace_access(workspace_id, user)
    return build_comparative_table_model(workspace_id)


@router.get("/{workspace_id}/m16/domains", response_model=list[EvaluationDomainOut])
def m16_list_domains(
    workspace_id: str,
    user: UserClaims = Depends(get_current_user),
):
    require_workspace_access(workspace_id, user)
    with get_connection() as conn:
        rows = m16_evaluation_service.list_evaluation_domains(conn, workspace_id)
    return [
        EvaluationDomainOut(
            id=r["id"],
            workspace_id=workspace_id,
            code=str(r.get("code") or ""),
            label=str(r.get("label") or ""),
            display_order=int(r.get("display_order") or 0),
        )
        for r in rows
    ]


@router.get(
    "/{workspace_id}/m16/criterion-assessments",
    response_model=list[CriterionAssessmentOut],
)
def m16_list_assessments(
    workspace_id: str,
    bundle_id: str | None = None,
    user: UserClaims = Depends(get_current_user),
):
    require_workspace_access(workspace_id, user)
    with get_connection() as conn:
        rows = m16_evaluation_service.list_criterion_assessments(
            conn, workspace_id, bundle_id=bundle_id
        )
    out: list[CriterionAssessmentOut] = []
    for r in rows:
        cj = r.get("cell_json")
        if not isinstance(cj, dict):
            cj = {}
        out.append(
            CriterionAssessmentOut(
                id=r["id"],
                workspace_id=str(r.get("workspace_id") or workspace_id),
                bundle_id=str(r.get("bundle_id")),
                criterion_key=str(r.get("criterion_key") or ""),
                dao_criterion_id=r.get("dao_criterion_id"),
                evaluation_document_id=r.get("evaluation_document_id"),
                cell_json=cj,
                assessment_status=str(r.get("assessment_status") or "draft"),
                confidence=r.get("confidence"),
            )
        )
    return out


@router.post(
    "/{workspace_id}/m16/initialize-from-m14",
    response_model=M16InitializeResult,
)
def m16_initialize_from_m14(
    workspace_id: str,
    user: UserClaims = Depends(get_current_user),
):
    require_workspace_permission(workspace_id, user, "workspace.update")
    try:
        raw = initialize_criterion_assessments_from_m14(workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return M16InitializeResult(
        workspace_id=str(raw["workspace_id"]),
        inserted=int(raw["inserted"]),
        skipped_existing=int(raw["skipped_existing"]),
        skipped_unknown_bundle=int(raw["skipped_unknown_bundle"]),
        evaluation_document_id=raw.get("evaluation_document_id"),
    )


@router.get(
    "/{workspace_id}/m16/targets/{target_type}/{target_id}/frame",
    response_model=M16EvaluationFrameOut,
)
def m16_evaluation_frame(
    workspace_id: str,
    target_type: TargetType,
    target_id: str,
    user: UserClaims = Depends(get_current_user),
):
    require_workspace_access(workspace_id, user)
    if target_type == TargetType.workspace and target_id != workspace_id:
        raise HTTPException(
            status_code=400,
            detail="target_id doit correspondre au workspace pour target_type=workspace",
        )
    bundle_filter: str | None = None
    if target_type == TargetType.bundle:
        bundle_filter = target_id

    with get_connection() as conn:
        if target_type == TargetType.session:
            sess = db_execute_one(
                conn,
                """
                SELECT id::text AS id FROM committee_sessions
                WHERE id = CAST(:sid AS uuid)
                  AND workspace_id = CAST(:wid AS uuid)
                """,
                {"sid": target_id, "wid": workspace_id},
            )
            if not sess:
                raise HTTPException(
                    status_code=404, detail="Session introuvable pour ce workspace"
                )
        if target_type == TargetType.bundle:
            b = db_execute_one(
                conn,
                """
                SELECT id::text AS id FROM supplier_bundles
                WHERE id = CAST(:bid AS uuid)
                  AND workspace_id = CAST(:wid AS uuid)
                """,
                {"bid": target_id, "wid": workspace_id},
            )
            if not b:
                raise HTTPException(
                    status_code=404, detail="Bundle introuvable pour ce workspace"
                )
        domains = m16_evaluation_service.list_evaluation_domains(conn, workspace_id)
        assessments = m16_evaluation_service.list_criterion_assessments(
            conn, workspace_id, bundle_id=bundle_filter
        )
        price_lines = m16_evaluation_service.list_price_lines(conn, workspace_id)
        price_vals = m16_evaluation_service.list_price_bundle_values(conn, workspace_id)

    return M16EvaluationFrameOut(
        workspace_id=workspace_id,
        target_type=target_type,
        target_id=target_id,
        domains=[
            EvaluationDomainOut(
                id=r["id"],
                workspace_id=workspace_id,
                code=str(r.get("code") or ""),
                label=str(r.get("label") or ""),
                display_order=int(r.get("display_order") or 0),
            )
            for r in domains
        ],
        assessments=[
            CriterionAssessmentOut(
                id=r["id"],
                workspace_id=workspace_id,
                bundle_id=str(r.get("bundle_id")),
                criterion_key=str(r.get("criterion_key") or ""),
                dao_criterion_id=r.get("dao_criterion_id"),
                evaluation_document_id=r.get("evaluation_document_id"),
                cell_json=(
                    r.get("cell_json") if isinstance(r.get("cell_json"), dict) else {}
                ),
                assessment_status=str(r.get("assessment_status") or "draft"),
                confidence=r.get("confidence"),
            )
            for r in assessments
        ],
        price_lines=[
            PriceLineComparisonOut(
                id=r["id"],
                line_code=str(r.get("line_code") or ""),
                label=r.get("label"),
                unit=r.get("unit"),
            )
            for r in price_lines
        ],
        price_values=[
            PriceLineBundleValueOut(
                id=r["id"],
                price_line_id=str(r.get("price_line_id")),
                bundle_id=str(r.get("bundle_id")),
                amount=r.get("amount"),
                currency=str(r.get("currency") or "XOF"),
            )
            for r in price_vals
        ],
    )


@router.get(
    "/{workspace_id}/m16/deliberation/threads",
    response_model=list[DeliberationThreadOut],
)
def m16_list_threads(
    workspace_id: str,
    user: UserClaims = Depends(get_current_user),
):
    require_workspace_access(workspace_id, user)
    with get_connection() as conn:
        rows = m16_deliberation_service.list_threads(conn, workspace_id)
    return [
        DeliberationThreadOut(
            id=r["id"],
            workspace_id=workspace_id,
            committee_session_id=r.get("committee_session_id"),
            title=str(r.get("title") or ""),
            thread_status=str(r.get("thread_status") or "open"),
        )
        for r in rows
    ]


@router.post(
    "/{workspace_id}/m16/deliberation/threads",
    response_model=DeliberationThreadOut,
)
def m16_create_thread(
    workspace_id: str,
    payload: DeliberationThreadCreate,
    user: UserClaims = Depends(get_current_user),
):
    require_workspace_permission(workspace_id, user, "workspace.update")
    with get_connection() as conn:
        ws = m16_evaluation_service.resolve_workspace_tenant(conn, workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace introuvable")
        tid = m16_deliberation_service.insert_thread(
            conn,
            workspace_id=workspace_id,
            tenant_id=str(ws["tenant_id"]),
            title=payload.title,
            committee_session_id=payload.committee_session_id,
        )
        found = m16_deliberation_service.get_thread(conn, workspace_id, tid)
    if not found:
        raise HTTPException(status_code=500, detail="Thread créé mais non relu")
    return DeliberationThreadOut(
        id=found["id"],
        workspace_id=workspace_id,
        committee_session_id=found.get("committee_session_id"),
        title=str(found.get("title") or ""),
        thread_status=str(found.get("thread_status") or "open"),
    )


@router.get(
    "/{workspace_id}/m16/deliberation/threads/{thread_id}/messages",
    response_model=list[DeliberationMessageOut],
)
def m16_list_messages(
    workspace_id: str,
    thread_id: str,
    user: UserClaims = Depends(get_current_user),
):
    require_workspace_access(workspace_id, user)
    with get_connection() as conn:
        rows = m16_deliberation_service.list_messages(conn, thread_id)
    return [
        DeliberationMessageOut(
            id=r["id"],
            thread_id=str(r.get("thread_id")),
            author_user_id=int(r.get("author_user_id") or 0),
            body=str(r.get("body") or ""),
            created_at=_iso(r.get("created_at")),
        )
        for r in rows
    ]


@router.post(
    "/{workspace_id}/m16/deliberation/threads/{thread_id}/messages",
    response_model=DeliberationMessageOut,
)
def m16_post_message(
    workspace_id: str,
    thread_id: str,
    payload: DeliberationMessageCreate,
    user: UserClaims = Depends(get_current_user),
):
    require_workspace_permission(workspace_id, user, "workspace.update")
    with get_connection() as conn:
        ws = m16_evaluation_service.resolve_workspace_tenant(conn, workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace introuvable")
        mid = m16_deliberation_service.insert_message(
            conn,
            thread_id=thread_id,
            workspace_id=workspace_id,
            tenant_id=str(ws["tenant_id"]),
            author_user_id=int(user.user_id),
            body=payload.body,
        )
        row = db_execute_one(
            conn,
            """
            SELECT id::text AS id, thread_id::text AS thread_id,
                   author_user_id, body, created_at
            FROM deliberation_messages
            WHERE id = CAST(:id AS uuid)
            """,
            {"id": mid},
        )
    if not row:
        raise HTTPException(status_code=500, detail="Message non relu")
    return DeliberationMessageOut(
        id=row["id"],
        thread_id=str(row.get("thread_id")),
        author_user_id=int(row.get("author_user_id") or 0),
        body=str(row.get("body") or ""),
        created_at=_iso(row.get("created_at")),
    )


@router.get(
    "/{workspace_id}/m16/comparative-shell",
    response_class=HTMLResponse,
    include_in_schema=True,
)
def m16_comparative_shell(
    workspace_id: str,
    user: UserClaims = Depends(get_current_user),
):
    """Coquille HTML (lecture seule) — liens vers les endpoints JSON M16."""
    require_workspace_access(workspace_id, user)
    base_dir = Path(__file__).resolve().parents[3]
    templates_dir = base_dir / "templates"
    env = build_jinja_env(str(templates_dir))
    html = env.get_template("comparative/shell.html.j2").render(
        workspace_id=workspace_id,
    )
    return HTMLResponse(content=html)
