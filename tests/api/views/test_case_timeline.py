"""Tests — Case Timeline view."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.views.case_timeline import get_case_timeline
from src.api.views.case_timeline_models import CaseTimeline, TimelineEvent


class TestGetCaseTimeline:
    def test_no_connection_returns_empty(self) -> None:
        result = get_case_timeline("CASE-001")
        assert isinstance(result, CaseTimeline)
        assert result.case_id == "CASE-001"
        assert result.events == []
        assert result.total_events == 0

    def test_accepts_limit(self) -> None:
        result = get_case_timeline("CASE-001", limit=10)
        assert result.total_events == 0


class TestTimelineEvent:
    def test_valid(self) -> None:
        e = TimelineEvent(
            event_id="e1",
            event_type="m13_regime_resolved",
            event_domain="procurement",
            event_time="2026-01-01T00:00:00Z",
        )
        assert e.event_id == "e1"

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            TimelineEvent(
                event_id="e1",
                event_type="t",
                event_domain="d",
                event_time="now",
                rogue="x",
            )


class TestCaseTimelineModel:
    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            CaseTimeline(case_id="C", rogue="x")
