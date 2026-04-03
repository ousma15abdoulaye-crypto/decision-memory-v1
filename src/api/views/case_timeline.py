"""Case timeline view — aggregates events from dms_event_index by case."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.views.case_timeline_models import CaseTimeline, TimelineEvent
from src.db.connection import get_db_cursor
from src.db.cursor_adapter import PsycopgCursorAdapter
from src.memory.event_index_service import EventIndexService

router = APIRouter(prefix="/views", tags=["views"])


@router.get("/case/{case_id}/timeline", response_model=CaseTimeline)
def get_case_timeline(case_id: str, limit: int = 50) -> CaseTimeline:
    try:
        with get_db_cursor() as cur:
            conn = PsycopgCursorAdapter(cur)
            svc = EventIndexService(lambda: conn)  # noqa: B023
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
