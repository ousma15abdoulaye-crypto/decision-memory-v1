"""Unit tests for M14 Pydantic models (extra=forbid, confidence grid)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.procurement.m14_evaluation_models import (
    CompletionAnalysis,
    EligibilityCheckResult,
    EvaluationMeta,
    EvaluationReport,
    M14EvaluationInput,
    OfferEvaluation,
    PriceAnalysis,
    TechnicalCriterionScore,
    TechnicalScore,
)


class TestExtraForbid:
    """E-49: all M14 models reject unknown fields."""

    @pytest.mark.parametrize(
        "model_cls,kwargs",
        [
            (
                EligibilityCheckResult,
                {"check_id": "G1", "check_name": "NIF", "result": "PASS"},
            ),
            (TechnicalCriterionScore, {"criteria_name": "method"}),
            (TechnicalScore, {}),
            (PriceAnalysis, {}),
            (CompletionAnalysis, {}),
            (OfferEvaluation, {"offer_document_id": "d1"}),
            (EvaluationMeta, {}),
            (EvaluationReport, {"case_id": "c1", "evaluation_method": "unknown"}),
            (M14EvaluationInput, {"case_id": "c1"}),
        ],
    )
    def test_rejects_extra(self, model_cls: type, kwargs: dict) -> None:
        kwargs["extra_bad_field"] = 42
        with pytest.raises(ValidationError):
            model_cls(**kwargs)


class TestConfidenceGrid:
    """Confidence values must be in {0.6, 0.8, 1.0}."""

    def test_valid_confidences(self) -> None:
        for c in (0.6, 0.8, 1.0):
            r = EligibilityCheckResult(
                check_id="G1", check_name="test", result="PASS", confidence=c
            )
            assert r.confidence == c

    def test_invalid_confidence_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EligibilityCheckResult(
                check_id="G1", check_name="test", result="PASS", confidence=0.5
            )


class TestEvaluationReport:
    def test_kill_list_fields_not_in_schema(self) -> None:
        """RÈGLE-09: fields winner/rank/recommendation/best_offer cause ValidationError."""
        for field_name in ("winner", "rank", "recommendation", "best_offer"):
            with pytest.raises(ValidationError):
                EvaluationReport(
                    case_id="c1",
                    evaluation_method="unknown",
                    **{field_name: "anything"},
                )

    def test_valid_evaluation_methods(self) -> None:
        for method in (
            "lowest_price",
            "mieux_disant",
            "quality_cost_based",
            "fixed_budget",
            "consultant_qualification",
            "unknown",
        ):
            r = EvaluationReport(case_id="c1", evaluation_method=method)
            assert r.evaluation_method == method

    def test_invalid_evaluation_method(self) -> None:
        with pytest.raises(ValidationError):
            EvaluationReport(case_id="c1", evaluation_method="best_value")
