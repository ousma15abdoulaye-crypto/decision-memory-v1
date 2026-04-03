"""Case timeline view — aggregates events from dms_event_index by case."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.api.views.case_timeline_models import CaseTimeline, TimelineEvent

router = APIRouter(prefix="/views", tags=["views"])


def _get_connection() -> Any:
    return None


@router.get("/case/{case_id}/timeline", response_model=CaseTimeline)
def get_case_timeline(case_id: str, limit: int = 50) -> CaseTimeline:
    conn = _get_connection()
    if conn is None:
        return CaseTimeline(case_id=case_id, events=[], total_events=0)

    try:
        from src.memory.event_index_service import EventIndexService

        svc = EventIndexService(lambda: conn)
        entries = svc.case_timeline(case_id, limit=limit)
        events = [
            TimelineEvent(
                event_id=e.event_id,
                event_type=e.event_type,
                event_domain=e.event_domain,
                event_time=e.event_time,
                summary=e.summary,
            )
            for e in entries
        ]
        return CaseTimeline(
            case_id=case_id,
            events=events,
            total_events=len(events),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
