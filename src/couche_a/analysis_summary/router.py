"""
src/couche_a/analysis_summary/router.py

Endpoints moteur analysis_summary — #12.
Agnostique : zéro logique STC, zéro appel pipeline, zéro Couche B.

Convention HTTP (cohérente avec M10 router) :
  HTTP 200 toujours + summary_status dans SummaryDocument
  HTTP 422 : validation Pydantic uniquement (triggered_by)
  HTTP 404 : GET /last si aucun résumé
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from psycopg.rows import dict_row

from src.couche_a.analysis_summary.engine.models import (
    SummaryDocument,
    SummaryGenerateRequest,
)
from src.couche_a.analysis_summary.engine.service import generate_summary

router = APIRouter(prefix="/api/cases", tags=["analysis-summary"])


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


@router.post(
    "/{case_id}/analysis-summary/generate",
    response_model=SummaryDocument,
    status_code=200,
    summary="Génère un SummaryDocument v1 depuis le CAS v1 persisté",
)
def generate_analysis_summary(
    case_id: str,
    body: SummaryGenerateRequest,
    conn=Depends(_get_conn),
) -> SummaryDocument:
    """
    Génère et persiste un SummaryDocument v1 depuis pipeline_runs.result_jsonb.

    HTTP 200 toujours + summary_status dans le payload :
      ready    → CAS partial_complete → résumé prêt pour M13
      partial  → CAS incomplete → résumé partiel
      blocked  → aucun pipeline_run trouvé
      failed   → CAS malformé / version incompatible

    HTTP 422 si triggered_by vide ou > 255 caractères.
    Zéro déclenchement pipeline. Zéro Couche B.
    """
    return generate_summary(
        case_id=case_id,
        triggered_by=body.triggered_by,
        conn=conn,
        pipeline_run_id=body.pipeline_run_id,
    )


@router.get(
    "/{case_id}/analysis-summary/last",
    response_model=SummaryDocument,
    status_code=200,
    summary="Dernier SummaryDocument pour ce dossier",
)
def get_last_analysis_summary(
    case_id: str,
    conn=Depends(_get_conn),
) -> SummaryDocument:
    """
    Retourne le dernier SummaryDocument persisté pour ce case_id.
    HTTP 404 si aucun résumé.

    Ordre : ORDER BY created_at DESC, summary_id DESC
    Déterministe : summary_id UUID tie-breaker.
    Le SummaryDocument est retourné depuis result_jsonb sans recalcul.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT result_jsonb
            FROM public.analysis_summaries
            WHERE case_id = %s
            ORDER BY created_at DESC, summary_id DESC
            LIMIT 1
            """,
            (case_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun résumé d'analyse trouvé pour case_id '{case_id}'.",
        )

    jsonb_raw = row["result_jsonb"] if isinstance(row, dict) else row[0]
    data = jsonb_raw if isinstance(jsonb_raw, dict) else json.loads(jsonb_raw)
    return SummaryDocument(**data)
