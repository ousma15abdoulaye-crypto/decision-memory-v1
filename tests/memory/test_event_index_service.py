"""Tests — EventIndexService (append, timeline, count)."""

from __future__ import annotations

from typing import Any

import pytest

from src.memory.event_index_models import CaseTimelineEntry, EventDomain, EventEntry
from src.memory.event_index_service import EventIndexService


class MockConn:
    def __init__(self) -> None:
        self.last_sql: str = ""
        self.last_params: dict[str, Any] | None = None
        self._fetchone_result: dict[str, Any] | None = None
        self._fetchall_result: list[dict[str, Any]] = []

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        self.last_sql = sql
        self.last_params = params

    def fetchone(self) -> dict[str, Any] | None:
        return self._fetchone_result

    def fetchall(self) -> list[dict[str, Any]]:
        return self._fetchall_result

    def set_fetchone(self, result: dict[str, Any] | None) -> None:
        self._fetchone_result = result

    def set_fetchall(self, result: list[dict[str, Any]]) -> None:
        self._fetchall_result = result


def _entry(**kw: Any) -> EventEntry:
    defaults: dict[str, Any] = {
        "event_domain": EventDomain.procurement,
        "source_table": "m13_correction_log",
        "source_pk": 1,
        "aggregate_type": "case",
        "event_type": "m13_correction_applied",
        "event_time": "2026-01-01T00:00:00Z",
    }
    defaults.update(kw)
    return EventEntry(**defaults)


class TestAppend:
    def test_returns_event_id(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"event_id": "abc-123"})
        svc = EventIndexService(lambda: conn)
        eid = svc.append(_entry())
        assert eid == "abc-123"
        assert "INSERT INTO dms_event_index" in conn.last_sql

    def test_raises_on_no_returning(self) -> None:
        conn = MockConn()
        conn.set_fetchone(None)
        svc = EventIndexService(lambda: conn)
        with pytest.raises(RuntimeError, match="RETURNING event_id"):
            svc.append(_entry())

    def test_params_complete(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"event_id": "x"})
        svc = EventIndexService(lambda: conn)
        svc.append(_entry(case_id="CASE-1"))
        assert conn.last_params is not None
        assert conn.last_params["case_id"] == "CASE-1"
        assert conn.last_params["event_domain"] == "procurement"


class TestTimeline:
    def test_returns_entries(self) -> None:
        conn = MockConn()
        conn.set_fetchall(
            [
                {
                    "event_id": "e1",
                    "event_type": "m13_correction_applied",
                    "event_domain": "procurement",
                    "event_time": "2026-01-01T00:00:00Z",
                    "summary": {},
                }
            ]
        )
        svc = EventIndexService(lambda: conn)
        entries = svc.case_timeline("CASE-1")
        assert len(entries) == 1
        assert isinstance(entries[0], CaseTimelineEntry)
        assert entries[0].event_id == "e1"

    def test_limit_validation(self) -> None:
        conn = MockConn()
        svc = EventIndexService(lambda: conn)
        with pytest.raises(ValueError, match="limit must be >= 1"):
            svc.case_timeline("CASE-1", limit=0)

    def test_summary_json_string_parsed(self) -> None:
        conn = MockConn()
        conn.set_fetchall(
            [
                {
                    "event_id": "e2",
                    "event_type": "t",
                    "event_domain": "d",
                    "event_time": "now",
                    "summary": '{"k": "v"}',
                }
            ]
        )
        svc = EventIndexService(lambda: conn)
        entries = svc.case_timeline("C")
        assert entries[0].summary == {"k": "v"}


class TestCountByDomain:
    def test_returns_count(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"c": 42})
        svc = EventIndexService(lambda: conn)
        assert svc.count_by_domain(EventDomain.procurement) == 42

    def test_returns_zero_on_none(self) -> None:
        conn = MockConn()
        conn.set_fetchone(None)
        svc = EventIndexService(lambda: conn)
        assert svc.count_by_domain(EventDomain.market) == 0


class TestEventEntryModel:
    def test_extra_forbid(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="extra"):
            EventEntry(
                event_domain=EventDomain.procurement,
                source_table="t",
                source_pk=1,
                aggregate_type="a",
                event_type="e",
                event_time="now",
                rogue="x",
            )
