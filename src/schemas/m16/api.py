"""Modèles API M16 — FastAPI + sérialisation JSON."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.models.m16_enums import TargetType


class EvaluationDomainOut(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    workspace_id: str
    code: str
    label: str
    display_order: int = 0


class CriterionAssessmentOut(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    workspace_id: str
    bundle_id: str
    criterion_key: str
    dao_criterion_id: str | None = None
    evaluation_document_id: str | None = None
    cell_json: dict[str, Any] = Field(default_factory=dict)
    assessment_status: str
    confidence: float | None = None
    signal: str | None = None
    computed_weighted_contribution: float | None = None


class DeliberationThreadOut(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    workspace_id: str
    committee_session_id: str | None = None
    title: str
    thread_status: str


class DeliberationMessageOut(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    thread_id: str
    author_user_id: int
    body: str
    created_at: str | None = None


class DeliberationThreadCreate(BaseModel):
    model_config = {"extra": "forbid"}

    title: str = ""
    committee_session_id: str | None = None


class DeliberationMessageCreate(BaseModel):
    model_config = {"extra": "forbid"}

    body: str = Field(..., min_length=1)


class PriceLineComparisonOut(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    line_code: str
    label: str | None = None
    unit: str | None = None


class PriceLineBundleValueOut(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    price_line_id: str
    bundle_id: str
    amount: str | None = None
    currency: str = "XOF"
    market_delta_pct: float | None = None
    price_signal: str | None = None


class M16EvaluationFrameOut(BaseModel):
    model_config = {"extra": "forbid"}

    workspace_id: str
    target_type: TargetType
    target_id: str
    domains: list[EvaluationDomainOut] = Field(default_factory=list)
    assessments: list[CriterionAssessmentOut] = Field(default_factory=list)
    price_lines: list[PriceLineComparisonOut] = Field(default_factory=list)
    price_values: list[PriceLineBundleValueOut] = Field(default_factory=list)
    bundle_weighted_totals: dict[str, float | None] = Field(default_factory=dict)
    weight_validation: dict[str, Any] = Field(default_factory=dict)


class M16InitializeResult(BaseModel):
    model_config = {"extra": "forbid"}

    workspace_id: str
    inserted: int
    skipped_existing: int
    skipped_unknown_bundle: int
    evaluation_document_id: str | None = None
