"""
M14 — Evaluation Engine API routes.

ADR-M14-001. Auth Depends(get_current_user) sur toutes les routes.
Typed response models (GAP-3 / GAP-4 hardening).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.procurement.m14_engine import EvaluationEngine
from src.procurement.m14_evaluation_models import (
    EvaluationDocumentEnvelope,
    EvaluationReport,
    M14EvaluationInput,
    M14StatusResponse,
)
from src.procurement.m14_evaluation_repository import M14EvaluationRepository

router = APIRouter(prefix="/api/m14", tags=["m14-evaluation"])


@router.get(
    "/status",
    response_model=M14StatusResponse,
    responses={401: {"description": "Token manquant ou invalide"}},
)
def m14_status(
    _user: Annotated[UserClaims, Depends(get_current_user)],
) -> M14StatusResponse:
    """Indique que le module M14 est disponible."""
    return M14StatusResponse(
        module="M14 Evaluation Engine",
        version="1.0.0",
    )


@router.post(
    "/evaluate",
    response_model=EvaluationReport,
    responses={
        401: {"description": "Token manquant ou invalide"},
        422: {"description": "Validation input échouée (Pydantic)"},
    },
)
def m14_evaluate(
    body: M14EvaluationInput,
    _user: Annotated[UserClaims, Depends(get_current_user)],
) -> EvaluationReport:
    """Lance l'évaluation comparative pour un case.

    Retourne l'EvaluationReport typé. La persistance est tentée mais
    non bloquante (absence de comité = pas de sauvegarde en DB).
    """
    repo = M14EvaluationRepository()
    engine = EvaluationEngine(repository=repo)
    return engine.evaluate(body)


@router.get(
    "/evaluations/{case_id}",
    response_model=EvaluationDocumentEnvelope,
    responses={
        401: {"description": "Token manquant ou invalide"},
        404: {"description": "Aucune évaluation trouvée pour ce case"},
    },
)
def m14_get_evaluation(
    case_id: str,
    _user: Annotated[UserClaims, Depends(get_current_user)],
) -> EvaluationDocumentEnvelope:
    """Lit la dernière évaluation pour un case."""
    repo = M14EvaluationRepository()
    result = repo.get_latest(case_id=case_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune évaluation trouvée pour case_id={case_id}",
        )
    return EvaluationDocumentEnvelope.model_validate(result)
