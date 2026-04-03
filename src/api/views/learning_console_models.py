"""Pydantic models for learning console (VIVANT V2 H4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CorrectionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_corrections: int = 0
    correction_rate_30d: float = 0.0
    top_fields: list[str] = Field(default_factory=list)


class PatternSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern_type: str
    field_path: str | None = None
    occurrences: int = 0
    confidence: float = 0.0


class CandidateRuleSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    status: str
    change_type: str
    change_detail: str = ""


class LearningConsoleData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corrections: CorrectionSummary = Field(default_factory=CorrectionSummary)
    patterns: list[PatternSummary] = Field(default_factory=list)
    candidate_rules: list[CandidateRuleSummary] = Field(default_factory=list)
    calibration_status: str = "healthy"


class RuleActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    new_status: str
    message: str = ""


class RAGASHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluated_at: str
    overall_score: float
    context_precision: float
    faithfulness: float
    answer_relevancy: float
