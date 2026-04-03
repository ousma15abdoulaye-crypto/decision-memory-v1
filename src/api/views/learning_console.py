"""Learning console — corrections, patterns, candidate rules, RAGAS history."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.api.views.learning_console_models import (
    CandidateRuleSummary,
    LearningConsoleData,
    PatternSummary,
    RAGASHistoryEntry,
    RuleActionResponse,
)

router = APIRouter(prefix="/views/learning", tags=["learning"])


def _get_connection() -> Any:
    return None


@router.get("/console", response_model=LearningConsoleData)
def get_learning_console() -> LearningConsoleData:
    return LearningConsoleData()


@router.get("/patterns", response_model=list[PatternSummary])
def get_patterns() -> list[PatternSummary]:
    conn = _get_connection()
    if conn is None:
        return []

    try:
        from src.memory.pattern_detector import PatternDetector

        pd = PatternDetector(lambda: conn)
        detected = pd.detect_all()
        return [
            PatternSummary(
                pattern_type=p.pattern_type.value,
                field_path=p.field_path,
                occurrences=p.occurrences,
                confidence=p.confidence,
            )
            for p in detected
        ]
    except Exception:
        return []


@router.get("/rules", response_model=list[CandidateRuleSummary])
def get_candidate_rules(status: str | None = None) -> list[CandidateRuleSummary]:
    return []


@router.post("/rules/{rule_id}/approve", response_model=RuleActionResponse)
def approve_rule(rule_id: str) -> RuleActionResponse:
    return RuleActionResponse(
        rule_id=rule_id,
        new_status="approved",
        message=f"Rule {rule_id} approved",
    )


@router.post("/rules/{rule_id}/reject", response_model=RuleActionResponse)
def reject_rule(rule_id: str) -> RuleActionResponse:
    return RuleActionResponse(
        rule_id=rule_id,
        new_status="rejected",
        message=f"Rule {rule_id} rejected",
    )


@router.get("/ragas-history", response_model=list[RAGASHistoryEntry])
def get_ragas_history() -> list[RAGASHistoryEntry]:
    return []
