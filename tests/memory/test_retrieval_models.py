"""Tests — retrieval & event-index Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.memory.event_index_models import CaseTimelineEntry
from src.memory.retrieval_models import SimilarCaseResult


class TestSimilarCaseResult:
    def test_valid(self) -> None:
        r = SimilarCaseResult(
            case_id="C",
            similarity_score=0.7,
            framework="sci",
            procurement_family="goods",
        )
        assert r.case_id == "C"

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            SimilarCaseResult(
                case_id="C",
                similarity_score=0.5,
                framework="f",
                procurement_family="p",
                rogue="x",
            )

    def test_score_bounds_low(self) -> None:
        with pytest.raises(ValidationError):
            SimilarCaseResult(
                case_id="C",
                similarity_score=-0.1,
                framework="f",
                procurement_family="p",
            )

    def test_score_bounds_high(self) -> None:
        with pytest.raises(ValidationError):
            SimilarCaseResult(
                case_id="C",
                similarity_score=1.1,
                framework="f",
                procurement_family="p",
            )


class TestCaseTimelineEntry:
    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            CaseTimelineEntry(
                event_id="e",
                event_type="t",
                event_domain="d",
                event_time="now",
                summary={},
                rogue="x",
            )
