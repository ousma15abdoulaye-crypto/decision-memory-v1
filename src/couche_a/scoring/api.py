"""
M3B Scoring API endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.couche_a.auth.case_access import require_case_access
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.scoring.models import ScoringRequest
from src.db import db_fetchall, get_connection

router = APIRouter(prefix="/api/scoring", tags=["Scoring M3B"])


@router.post("/calculate")
async def calculate_scoring(
    request: ScoringRequest,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """
    Endpoint désactivé.
    Scoring déclenché exclusivement via pipeline FSM.
    Un appel direct bypasse les gardes et viole l'atomicité.
    Disponible : intégration pipeline M9.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "error": "scoring_direct_disabled",
            "message": (
                "Scoring via pipeline FSM uniquement. " "Endpoint direct désactivé."
            ),
            "available_at": "M9",
        },
    )


@router.get("/{case_id}/scores")
async def get_scores(
    case_id: str,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Retrieve calculated scores for a case."""
    require_case_access(case_id, user)

    try:
        with get_connection() as conn:
            scores = db_fetchall(
                conn,
                """
                SELECT supplier_name, category, score_value,
                       calculation_method, calculation_details,
                       is_validated, created_at
                FROM supplier_scores
                WHERE case_id = :case_id
                ORDER BY category, score_value DESC
            """,
                {"case_id": case_id},
            )

        return {
            "case_id": case_id,
            "scores": [
                {
                    "supplier_name": s["supplier_name"],
                    "category": s["category"],
                    "score_value": float(s["score_value"]),
                    "calculation_method": s["calculation_method"],
                    "is_validated": s["is_validated"],
                    "created_at": s["created_at"],
                }
                for s in scores
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve scores: {str(e)}"
        )
