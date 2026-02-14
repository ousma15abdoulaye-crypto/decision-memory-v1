"""
Pydantic models for M3B Scoring Engine.
Constitution V3 compliant: Non-prescriptive scoring.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

__all__ = ["ScoreResult", "EliminationResult", "ScoringRequest", "ScoringResponse"]


class ScoreResult(BaseModel):
    """Score result for a supplier in a category."""
    supplier_name: str
    category: str  # 'commercial', 'capacity', 'sustainability', 'essentials', 'total'
    score_value: float = Field(..., ge=0, le=100)
    calculation_method: str
    calculation_details: Dict[str, Any] = Field(default_factory=dict)
    is_validated: bool = False
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None


class EliminationResult(BaseModel):
    """Elimination result for a supplier."""
    supplier_name: str
    criterion_id: str
    criterion_name: str
    criterion_category: str
    failure_reason: str
    eliminated_at: datetime = Field(default_factory=datetime.utcnow)


class ScoringRequest(BaseModel):
    """Request to calculate scores for a case."""
    case_id: str
    recalculate: bool = False  # Force recalculation even if scores exist


class ScoringResponse(BaseModel):
    """Response after scoring calculation."""
    case_id: str
    scores_count: int
    eliminations_count: int
    calculation_time_ms: float
    status: str  # 'success', 'partial', 'failed'
    errors: list[str] = Field(default_factory=list)