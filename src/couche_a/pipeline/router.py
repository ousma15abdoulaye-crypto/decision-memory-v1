# src/couche_a/pipeline/router.py
"""
Router Pipeline A — POST /run + GET /last.

Convention HTTP (ADR-0012) :
  Toujours HTTP 200 + status métier dans le payload.
  Aucun 409/422/500 pour des statuts métier (blocked/incomplete/failed).
  HTTP 404 uniquement sur GET /last si aucun run trouvé.
  Zéro logique métier dans le router.

Compat backward #10 (INV-API-11-01) :
  POST /run sans body → mode='partial', force_recompute=False.
  Body minimal {"triggered_by": "..."} accepté.
"""

from __future__ import annotations

import os
from collections.abc import Generator

import psycopg
from fastapi import APIRouter, Body, Depends, HTTPException
from psycopg.rows import dict_row

from . import service
from .models import PipelineLastRunResponse, PipelineResult, PipelineRunRequest

router = APIRouter(prefix="/api/cases", tags=["pipeline"])


def _get_conn() -> Generator[psycopg.Connection, None, None]:
    """Dependency FastAPI : connexion psycopg autocommit=False, dict_row."""
    url = os.environ.get("DATABASE_URL", "").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    conn = psycopg.connect(url, row_factory=dict_row, autocommit=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@router.post("/{case_id}/pipeline/a/run", response_model=PipelineResult)
def run_pipeline_a(
    case_id: str,
    body: PipelineRunRequest = Body(default_factory=PipelineRunRequest),
    conn: psycopg.Connection = Depends(_get_conn),
) -> PipelineResult:
    """
    Lance le pipeline A pour un dossier.

    Dispatch vers run_pipeline_a_partial ou run_pipeline_a_e2e selon body.mode.
    Compat backward #10 : body optionnel, mode='partial', force_recompute=False.
    Toujours HTTP 200 — le statut métier est dans PipelineResult.status.
    blocked/incomplete/failed ne sont pas des erreurs HTTP.
    INV-API-11-01 : zéro logique métier ici.
    """
    if body.mode == "e2e":
        return service.run_pipeline_a_e2e(
            case_id=case_id,
            triggered_by=body.triggered_by,
            conn=conn,
            force_recompute=body.force_recompute,
        )
    return service.run_pipeline_a_partial(
        case_id=case_id,
        triggered_by=body.triggered_by,
        conn=conn,
    )


@router.get("/{case_id}/pipeline/a/last", response_model=PipelineLastRunResponse)
def get_last_pipeline_a_run(
    case_id: str,
    conn: psycopg.Connection = Depends(_get_conn),
) -> PipelineLastRunResponse:
    """
    Récupère le dernier run du pipeline A pour un dossier.
    Lit depuis result_jsonb — pas de recalcul (INV-P9).
    HTTP 404 si aucun run trouvé.
    """
    result = service.get_last_pipeline_run(case_id=case_id, conn=conn)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun run pipeline A trouvé pour case_id={case_id!r}",
        )
    return result
