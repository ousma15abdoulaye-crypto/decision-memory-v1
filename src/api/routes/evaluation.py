"""
M14 — Evaluation Engine API routes.

ADR-M14-001. Auth Depends(get_current_user) sur toutes les routes.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.procurement.m14_engine import EvaluationEngine
from src.procurement.m14_evaluation_models import EvaluationReport, M14EvaluationInput
from src.procurement.m14_evaluation_repository import M14EvaluationRepository

router = APIRouter(prefix="/api/m14", tags=["m14-evaluation"])


@router.get("/status")
def m14_status(
    _user: Annotated[UserClaims, Depends(get_current_user)],
) -> dict[str, str]:
    """Indique que le module M14 est disponible."""
    return {
        "module": "M14 Evaluation Engine",
        "version": "1.0.0",
    }


@router.post("/evaluate")
def m14_evaluate(
    body: M14EvaluationInput,
    _user: Annotated[UserClaims, Depends(get_current_user)],
) -> dict[str, Any]:
    """Lance l'évaluation comparative pour un case.

    Retourne l'EvaluationReport sérialisé + l'id de persistance.
    """
    repo = M14EvaluationRepository()
    engine = EvaluationEngine(repository=repo)
    report: EvaluationReport = engine.evaluate(body)
    return report.model_dump(mode="json")


@router.get("/evaluations/{case_id}")
def m14_get_evaluation(
    case_id: str,
    _user: Annotated[UserClaims, Depends(get_current_user)],
) -> dict[str, Any]:
    """Lit la dernière évaluation pour un case."""
    repo = M14EvaluationRepository()
    result = repo.get_latest(case_id=case_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune évaluation trouvée pour case_id={case_id}",
        )
    return result
