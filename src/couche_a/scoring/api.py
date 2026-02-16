"""
M3B Scoring API endpoints.
"""

from fastapi import APIRouter, HTTPException
import time

from src.auth import CurrentUser
from src.db import get_connection, db_fetchall
from src.couche_a.scoring.models import ScoringRequest, ScoringResponse

router = APIRouter(prefix="/api/scoring", tags=["Scoring M3B"])


@router.post("/calculate", response_model=ScoringResponse)
async def calculate_scores(request: ScoringRequest, user: CurrentUser):
    """
    Calculate scores for a case (async background task in production).
    Constitution V3: Non-prescriptive, validation humaine requise.
    """
    start_time = time.time()

    try:
        # Load case data (stub - implement actual loading)
        # suppliers = load_suppliers_for_case(request.case_id)
        # criteria = load_criteria_for_case(request.case_id)

        # For now, return stub response
        return ScoringResponse(
            case_id=request.case_id,
            scores_count=0,
            eliminations_count=0,
            calculation_time_ms=(time.time() - start_time) * 1000,
            status="success",
            errors=[],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@router.get("/{case_id}/scores")
async def get_scores(case_id: str, user: CurrentUser):
    """Retrieve calculated scores for a case."""
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
