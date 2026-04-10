"""Routes M16 — comparatif contradictoire (cadre, backfill, délibération, prix).

Inclut les routes d'écriture price_line (Option B enterprise) :
  POST …/m16/price-lines              : créer une ligne comparatif
  POST …/m16/price-lines/{id}/values  : saisir un prix fournisseur (auto-refresh delta)
  POST …/m16/refresh-market-deltas    : recalcul batch delta marché (admin)
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi import status as http_status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.api.guards.m16_guards import m16_guard
from src.api.pagination import PaginationParams, paginated_response
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.workspace_access import require_workspace_access
from src.db import db_execute, db_execute_one, get_connection
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
from src.services.m14_bridge import BridgeResult, populate_assessments_from_m14
from src.services.m16_backfill import initialize_criterion_assessments_from_m14
from src.services.m16_frame_payload import enrich_assessments_for_frame
from src.services.market_delta import persist_market_deltas_for_workspace
from src.services.signal_engine import compute_price_signal
from src.utils.jinja_filters import build_jinja_env

router = APIRouter(prefix="/api/workspaces", tags=["m16-comparative"])


def _iso(dt: object | None) -> str | None:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _price_bundle_value_out(r: dict[str, Any]) -> PriceLineBundleValueOut:
    """Construit PriceLineBundleValueOut depuis une ligne DB (Option B — delta en base)."""
    raw_delta = r.get("market_delta_pct")
    delta: float | None = None
    if raw_delta is not None:
        try:
            delta = float(raw_delta)
        except (TypeError, ValueError):
            pass
    return PriceLineBundleValueOut(
        id=str(r["id"]),
        price_line_id=str(r.get("price_line_id")),
        bundle_id=str(r.get("bundle_id")),
        amount=r.get("amount"),
        currency=str(r.get("currency") or "XOF"),
        market_delta_pct=delta,
        price_signal=compute_price_signal(market_delta_pct=delta),
    )


def _assessment_out_from_row(
    workspace_id: str, r: dict[str, Any], **extra: Any
) -> CriterionAssessmentOut:
    cj = r.get("cell_json")
    if not isinstance(cj, dict):
        cj = {}
    return CriterionAssessmentOut(
        id=r["id"],
        workspace_id=str(r.get("workspace_id") or workspace_id),
        bundle_id=str(r.get("bundle_id")),
        criterion_key=str(r.get("criterion_key") or ""),
        dao_criterion_id=r.get("dao_criterion_id"),
        evaluation_document_id=r.get("evaluation_document_id"),
        cell_json=cj,
        assessment_status=str(r.get("assessment_status") or "draft"),
        confidence=r.get("confidence"),
        signal=extra.get("signal"),
        computed_weighted_contribution=extra.get("computed_weighted_contribution"),
    )


@router.get("/{workspace_id}/m16/comparative-table-model")
def m16_comparative_table_model_json(
    workspace_id: str,
    user: UserClaims = Depends(get_current_user),
):
    """Projection tableau comparatif (live DB), alignée XLSX/PDF — inclut M16 si présent."""
    m16_guard(workspace_id, user, min_cognitive="E3")
    return build_comparative_table_model(workspace_id)


@router.get("/{workspace_id}/m16/domains")
def m16_list_domains(
    workspace_id: str,
    page: int = 1,
    page_size: int = 50,
    user: UserClaims = Depends(get_current_user),
):
    m16_guard(workspace_id, user, min_cognitive="E0")
    params = PaginationParams(page=page, page_size=page_size)
    with get_connection() as conn:
        total = m16_evaluation_service.count_evaluation_domains(conn, workspace_id)
        rows = m16_evaluation_service.list_evaluation_domains_paged(
            conn, workspace_id, limit=params.limit, offset=params.offset
        )
    items = [
        EvaluationDomainOut(
            id=r["id"],
            workspace_id=workspace_id,
            code=str(r.get("code") or ""),
            label=str(r.get("label") or ""),
            display_order=int(r.get("display_order") or 0),
        )
        for r in rows
    ]
    return paginated_response(items=items, total=total, params=params, key="domains")


@router.get("/{workspace_id}/m16/criterion-assessments")
def m16_list_assessments(
    workspace_id: str,
    bundle_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
    user: UserClaims = Depends(get_current_user),
):
    m16_guard(workspace_id, user, min_cognitive="E0")
    params = PaginationParams(page=page, page_size=page_size)
    with get_connection() as conn:
        total = m16_evaluation_service.count_criterion_assessments(
            conn, workspace_id, bundle_id
        )
        rows = m16_evaluation_service.list_criterion_assessments_paged(
            conn,
            workspace_id,
            bundle_id,
            limit=params.limit,
            offset=params.offset,
        )
    out: list[CriterionAssessmentOut] = []
    for r in rows:
        cj = r.get("cell_json")
        if not isinstance(cj, dict):
            cj = {}
        out.append(
            _assessment_out_from_row(workspace_id, {**r, "cell_json": cj}),
        )
    return paginated_response(items=out, total=total, params=params, key="assessments")


@router.post("/{workspace_id}/m16/sync-from-m14")
def m16_sync_from_m14(
    workspace_id: str,
    user: UserClaims = Depends(get_current_user),
):
    """Synchronise criterion_assessments depuis evaluation_documents.scores_matrix.

    Version enterprise du bridge M14→M16 (Rupture R1) :
      - Crée les assessments manquants (source = "m14")
      - Met à jour les assessments sans score (cell_json->>'score' IS NULL)
      - Ignore les assessments avec score posé par l'évaluateur (RÈGLE-R1)

    Retourne un BridgeResult avec created / updated / skipped et les listes
    d'éléments non mappés pour diagnostics.
    """
    m16_guard(
        workspace_id,
        user,
        min_cognitive="E3",
        permission="evaluation.write",
        block_write_if_sealed=True,
    )
    try:
        result: BridgeResult = populate_assessments_from_m14(workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "workspace_id": result.workspace_id,
        "evaluation_document_id": result.evaluation_document_id,
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "unmapped_bundles": result.unmapped_bundles,
        "unmapped_criteria": result.unmapped_criteria,
        "errors": result.errors,
    }


@router.post(
    "/{workspace_id}/m16/initialize-from-m14",
    response_model=M16InitializeResult,
)
def m16_initialize_from_m14(
    workspace_id: str,
    user: UserClaims = Depends(get_current_user),
):
    m16_guard(
        workspace_id,
        user,
        min_cognitive="E3",
        permission="workspace.update",
        block_write_if_sealed=True,
    )
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
    m16_guard(workspace_id, user, min_cognitive="E3")
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
        assessments_raw = m16_evaluation_service.list_criterion_assessments(
            conn, workspace_id, bundle_id=bundle_filter
        )
        enriched, bundle_weighted_totals, weight_validation = (
            enrich_assessments_for_frame(conn, workspace_id, assessments_raw)
        )
        price_lines = m16_evaluation_service.list_price_lines(conn, workspace_id)
        price_vals = m16_evaluation_service.list_price_bundle_values(conn, workspace_id)

    assessments_out: list[CriterionAssessmentOut] = []
    for r in enriched:
        cj = r.get("cell_json")
        if not isinstance(cj, dict):
            cj = {}
        assessments_out.append(
            _assessment_out_from_row(
                workspace_id,
                {**r, "cell_json": cj},
                signal=r.get("signal"),
                computed_weighted_contribution=r.get("computed_weighted_contribution"),
            )
        )

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
        assessments=assessments_out,
        price_lines=[
            PriceLineComparisonOut(
                id=r["id"],
                line_code=str(r.get("line_code") or ""),
                label=r.get("label"),
                unit=r.get("unit"),
            )
            for r in price_lines
        ],
        price_values=[_price_bundle_value_out(r) for r in price_vals],
        bundle_weighted_totals=bundle_weighted_totals,
        weight_validation=weight_validation,
    )


@router.get("/{workspace_id}/m16/clarifications")
def m16_list_clarifications(
    workspace_id: str,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    user: UserClaims = Depends(get_current_user),
):
    m16_guard(workspace_id, user, min_cognitive="E4")
    params = PaginationParams(page=page, page_size=page_size)
    with get_connection() as conn:
        total = m16_evaluation_service.count_clarification_requests(
            conn, workspace_id, status
        )
        rows = m16_evaluation_service.list_clarification_requests_paged(
            conn, workspace_id, status, limit=params.limit, offset=params.offset
        )
    return paginated_response(
        items=[dict(r) for r in rows],
        total=total,
        params=params,
        key="clarifications",
    )


@router.get("/{workspace_id}/m16/validated-notes")
def m16_list_validated_notes(
    workspace_id: str,
    page: int = 1,
    page_size: int = 50,
    user: UserClaims = Depends(get_current_user),
):
    m16_guard(workspace_id, user, min_cognitive="E4")
    params = PaginationParams(page=page, page_size=page_size)
    with get_connection() as conn:
        total = m16_evaluation_service.count_validated_notes(conn, workspace_id)
        rows = m16_evaluation_service.list_validated_notes_paged(
            conn, workspace_id, limit=params.limit, offset=params.offset
        )
    return paginated_response(
        items=[dict(r) for r in rows],
        total=total,
        params=params,
        key="notes",
    )


@router.get(
    "/{workspace_id}/m16/targets/criterion-assessment/{assessment_id}/notes",
)
def m16_notes_by_assessment_target(
    workspace_id: str,
    assessment_id: str,
    user: UserClaims = Depends(get_current_user),
):
    m16_guard(workspace_id, user, min_cognitive="E4")
    with get_connection() as conn:
        ca = db_execute_one(
            conn,
            """
            SELECT id::text AS id FROM criterion_assessments
            WHERE id = CAST(:id AS uuid)
              AND workspace_id = CAST(:ws AS uuid)
            """,
            {"id": assessment_id, "ws": workspace_id},
        )
        if not ca:
            raise HTTPException(status_code=404, detail="Assessment introuvable")
        rows = m16_evaluation_service.list_validated_notes_for_assessment(
            conn, workspace_id, assessment_id
        )
    return {"notes": [dict(r) for r in rows]}


@router.get("/{workspace_id}/m16/criterion-assessments/{assessment_id}/history")
def m16_assessment_history(
    workspace_id: str,
    assessment_id: str,
    page: int = 1,
    page_size: int = 100,
    user: UserClaims = Depends(get_current_user),
):
    m16_guard(workspace_id, user, min_cognitive="E0")
    params = PaginationParams(page=page, page_size=page_size)
    with get_connection() as conn:
        ca = db_execute_one(
            conn,
            """
            SELECT id::text AS id FROM criterion_assessments
            WHERE id = CAST(:id AS uuid)
              AND workspace_id = CAST(:ws AS uuid)
            """,
            {"id": assessment_id, "ws": workspace_id},
        )
        if not ca:
            raise HTTPException(status_code=404, detail="Assessment introuvable")
        total = m16_evaluation_service.count_assessment_history(conn, assessment_id)
        rows = m16_evaluation_service.list_assessment_history_paged(
            conn, assessment_id, limit=params.limit, offset=params.offset
        )
    return paginated_response(
        items=[dict(r) for r in rows],
        total=total,
        params=params,
        key="history",
    )


@router.get("/{workspace_id}/m16/deliberation/threads")
def m16_list_threads(
    workspace_id: str,
    page: int = 1,
    page_size: int = 50,
    user: UserClaims = Depends(get_current_user),
):
    m16_guard(workspace_id, user, min_cognitive="E4")
    params = PaginationParams(page=page, page_size=page_size)
    with get_connection() as conn:
        total = m16_deliberation_service.count_threads(conn, workspace_id)
        rows = m16_deliberation_service.list_threads_paged(
            conn, workspace_id, limit=params.limit, offset=params.offset
        )
    items = [
        DeliberationThreadOut(
            id=r["id"],
            workspace_id=workspace_id,
            committee_session_id=r.get("committee_session_id"),
            title=str(r.get("title") or ""),
            thread_status=str(r.get("thread_status") or "open"),
        )
        for r in rows
    ]
    return paginated_response(items=items, total=total, params=params, key="threads")


@router.post(
    "/{workspace_id}/m16/deliberation/threads",
    response_model=DeliberationThreadOut,
)
def m16_create_thread(
    workspace_id: str,
    payload: DeliberationThreadCreate,
    user: UserClaims = Depends(get_current_user),
):
    m16_guard(
        workspace_id,
        user,
        min_cognitive="E4",
        permission="workspace.update",
        block_write_if_sealed=True,
    )
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


@router.get("/{workspace_id}/m16/deliberation/threads/{thread_id}/messages")
def m16_list_messages(
    workspace_id: str,
    thread_id: str,
    page: int = 1,
    page_size: int = 50,
    user: UserClaims = Depends(get_current_user),
):
    m16_guard(workspace_id, user, min_cognitive="E4")
    params = PaginationParams(page=page, page_size=page_size)
    with get_connection() as conn:
        thread = m16_deliberation_service.get_thread(conn, workspace_id, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread introuvable")
        total = m16_deliberation_service.count_messages(conn, workspace_id, thread_id)
        rows = m16_deliberation_service.list_messages_paged(
            conn,
            workspace_id,
            thread_id,
            limit=params.limit,
            offset=params.offset,
        )
    items = [
        DeliberationMessageOut(
            id=r["id"],
            thread_id=str(r.get("thread_id")),
            author_user_id=int(r.get("author_user_id") or 0),
            body=str(r.get("body") or ""),
            created_at=_iso(r.get("created_at")),
        )
        for r in rows
    ]
    return paginated_response(items=items, total=total, params=params, key="messages")


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
    m16_guard(
        workspace_id,
        user,
        min_cognitive="E4",
        permission="workspace.update",
        block_write_if_sealed=True,
    )
    with get_connection() as conn:
        thread = m16_deliberation_service.get_thread(conn, workspace_id, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread introuvable")
        mid = m16_deliberation_service.insert_message(
            conn,
            thread_id=str(thread["id"]),
            workspace_id=str(thread["workspace_id"]),
            tenant_id=str(thread.get("tenant_id") or ""),
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


# ── Routes write price-lines (Option B enterprise) ────────────────────────────


class PriceLineCreatePayload(BaseModel):
    model_config = {"extra": "forbid"}

    line_code: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=255)
    unit: str | None = None


class PriceLineBundleValueCreatePayload(BaseModel):
    model_config = {"extra": "forbid"}

    bundle_id: str = Field(..., description="UUID du bundle fournisseur")
    amount: str = Field(..., description="Montant numérique en string (ex: '125000')")
    currency: str = Field(default="XOF", max_length=8)


def _bg_refresh_delta(workspace_id: str) -> None:
    """Background task : recalcule le delta marché pour le workspace."""
    with get_connection() as conn:
        persist_market_deltas_for_workspace(conn, workspace_id)


@router.post(
    "/{workspace_id}/m16/price-lines",
    status_code=http_status.HTTP_201_CREATED,
)
def m16_create_price_line(
    workspace_id: str,
    payload: PriceLineCreatePayload,
    user: UserClaims = Depends(get_current_user),
):
    """Crée une ligne de comparatif prix pour ce workspace."""
    m16_guard(
        workspace_id,
        user,
        min_cognitive="E3",
        permission="evaluation.write",
        block_write_if_sealed=True,
    )
    with get_connection() as conn:
        ws = m16_evaluation_service.resolve_workspace_tenant(conn, workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace introuvable")
        tenant_id = str(ws["tenant_id"])

        existing = db_execute_one(
            conn,
            """
            SELECT id FROM price_line_comparisons
            WHERE workspace_id = CAST(:ws AS uuid)
              AND line_code = :code
            """,
            {"ws": workspace_id, "code": payload.line_code},
        )
        if existing:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=f"line_code {payload.line_code!r} déjà existant.",
            )

        line_id = str(uuid.uuid4())
        db_execute(
            conn,
            """
            INSERT INTO price_line_comparisons
                (id, workspace_id, tenant_id, line_code, label, unit)
            VALUES (CAST(:id AS uuid), CAST(:ws AS uuid), CAST(:tid AS uuid),
                    :code, :label, :unit)
            """,
            {
                "id": line_id,
                "ws": workspace_id,
                "tid": tenant_id,
                "code": payload.line_code,
                "label": payload.label,
                "unit": payload.unit,
            },
        )

    return {
        "id": line_id,
        "workspace_id": workspace_id,
        "line_code": payload.line_code,
        "label": payload.label,
        "unit": payload.unit,
    }


@router.post(
    "/{workspace_id}/m16/price-lines/{line_id}/values",
    status_code=http_status.HTTP_201_CREATED,
)
def m16_create_price_bundle_value(
    workspace_id: str,
    line_id: str,
    payload: PriceLineBundleValueCreatePayload,
    background_tasks: BackgroundTasks,
    user: UserClaims = Depends(get_current_user),
):
    """Saisit le prix d'un fournisseur pour une ligne comparatif.

    Déclenche automatiquement le recalcul market_delta_pct en background.
    """
    m16_guard(
        workspace_id,
        user,
        min_cognitive="E3",
        permission="evaluation.write",
        block_write_if_sealed=True,
    )
    with get_connection() as conn:
        line = db_execute_one(
            conn,
            """
            SELECT id, tenant_id FROM price_line_comparisons
            WHERE id = CAST(:lid AS uuid) AND workspace_id = CAST(:ws AS uuid)
            """,
            {"lid": line_id, "ws": workspace_id},
        )
        if not line:
            raise HTTPException(status_code=404, detail="Ligne prix introuvable.")

        tenant_id = str(line["tenant_id"])

        # Upsert : un seul montant par (price_line_id × bundle_id)
        value_id = str(uuid.uuid4())
        db_execute(
            conn,
            """
            INSERT INTO price_line_bundle_values
                (id, price_line_id, bundle_id, workspace_id, tenant_id,
                 amount, currency)
            VALUES (CAST(:id AS uuid), CAST(:lid AS uuid), CAST(:bid AS uuid),
                    CAST(:ws AS uuid), CAST(:tid AS uuid), :amount, :currency)
            ON CONFLICT (price_line_id, bundle_id)
            DO UPDATE SET amount   = EXCLUDED.amount,
                          currency = EXCLUDED.currency,
                          market_delta_pct        = NULL,
                          market_delta_computed_at = NULL
            """,
            {
                "id": value_id,
                "lid": line_id,
                "bid": payload.bundle_id,
                "ws": workspace_id,
                "tid": tenant_id,
                "amount": payload.amount,
                "currency": payload.currency,
            },
        )

    # Auto-refresh delta en background (non bloquant)
    background_tasks.add_task(_bg_refresh_delta, workspace_id)

    return {
        "workspace_id": workspace_id,
        "price_line_id": line_id,
        "bundle_id": payload.bundle_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "market_delta_status": "pending_refresh",
    }


@router.post("/{workspace_id}/m16/refresh-market-deltas")
def m16_refresh_market_deltas(
    workspace_id: str,
    user: UserClaims = Depends(get_current_user),
):
    """Recalcule market_delta_pct pour toutes les lignes prix du workspace.

    Appel synchrone — prévu pour admin ou suite à une MAJ des signaux marché.
    Retourne le compte mis à jour / sans signal.
    """
    m16_guard(
        workspace_id,
        user,
        min_cognitive="E3",
        permission="evaluation.write",
    )
    with get_connection() as conn:
        res = persist_market_deltas_for_workspace(conn, workspace_id)

    return {
        "workspace_id": workspace_id,
        "zone_id": res.zone_id,
        "total": res.total,
        "updated": res.updated,
        "no_signal": res.no_signal,
        "errors": res.errors,
    }


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
