"""Tests — Learning Console view."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.views.learning_console import (
    approve_rule,
    get_candidate_rules,
    get_learning_console,
    get_patterns,
    get_ragas_history,
    reject_rule,
)
from src.api.views.learning_console_models import (
    CandidateRuleSummary,
    CorrectionSummary,
    LearningConsoleData,
    PatternSummary,
    RAGASHistoryEntry,
    RuleActionResponse,
)


class TestGetLearningConsole:
    def test_returns_default(self) -> None:
        result = get_learning_console()
        assert isinstance(result, LearningConsoleData)
        assert result.calibration_status == "healthy"


class TestGetPatterns:
    def test_no_connection_returns_empty(self) -> None:
        result = get_patterns()
        assert result == []


class TestGetCandidateRules:
    def test_returns_empty(self) -> None:
        result = get_candidate_rules()
        assert result == []

    def test_with_status_filter(self) -> None:
        result = get_candidate_rules(status="proposed")
        assert result == []


class TestApproveRejectRule:
    def test_approve(self) -> None:
        result = approve_rule("rule-1")
        assert isinstance(result, RuleActionResponse)
        assert result.new_status == "approved"
        assert result.rule_id == "rule-1"

    def test_reject(self) -> None:
        result = reject_rule("rule-2")
        assert result.new_status == "rejected"


class TestGetRagasHistory:
    def test_returns_empty(self) -> None:
        assert get_ragas_history() == []


class TestModels:
    def test_correction_summary_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            CorrectionSummary(rogue="x")

    def test_pattern_summary_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            PatternSummary(pattern_type="t", occurrences=1, confidence=0.5, rogue="x")

    def test_candidate_rule_summary_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            CandidateRuleSummary(rule_id="r", status="s", change_type="c", rogue="x")

    def test_rule_action_response_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            RuleActionResponse(rule_id="r", new_status="s", rogue="x")

    def test_ragas_history_entry_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            RAGASHistoryEntry(
                evaluated_at="now",
                overall_score=0.5,
                context_precision=0.5,
                faithfulness=0.5,
                answer_relevancy=0.5,
                rogue="x",
            )
