"""Celery tasks for heavy / background processing."""

from __future__ import annotations

import asyncio

from backend.workers.celery_app import celery_app

__all__ = [
    "extract_document_task",
    "export_cba_task",
    "generate_pv_task",
    "process_outbox_task",
]


def _run_async(coro):
    """Helper to run an async function inside a sync Celery task."""
    return asyncio.run(coro)


@celery_app.task(name="dms.extract_document", bind=True, max_retries=3)
def extract_document_task(self, document_id: str, file_path: str):
    """Run document extraction asynchronously."""
    from backend.couche_a.analyzer import run_extraction
    from backend.system.db import async_session_factory

    async def _inner():
        async with async_session_factory() as db:
            await run_extraction(document_id, file_path, db)
            await db.commit()

    _run_async(_inner())


@celery_app.task(name="dms.export_cba", bind=True, max_retries=3)
def export_cba_task(self, case_id: str, lot_id: str, user_id: str):
    """Generate CBA export in background."""
    from backend.couche_a.cba_export import generate_cba_excel
    from backend.system.db import async_session_factory

    async def _inner():
        async with async_session_factory() as db:
            path = await generate_cba_excel(case_id, lot_id, db)
            await db.commit()
            return path

    return _run_async(_inner())


@celery_app.task(name="dms.generate_pv", bind=True, max_retries=3)
def generate_pv_task(self, case_id: str, lot_id: str, pv_type: str, user_id: str):
    """Generate PV document in background."""
    from backend.system.db import async_session_factory

    async def _inner():
        async with async_session_factory() as db:
            if pv_type == "opening":
                from backend.couche_a.pv_generator import generate_pv_opening
                path = await generate_pv_opening(case_id, lot_id, db)
            else:
                from backend.couche_a.pv_generator import generate_pv_analysis
                path = await generate_pv_analysis(case_id, lot_id, db)
            await db.commit()
            return path

    return _run_async(_inner())


@celery_app.task(name="dms.process_outbox")
def process_outbox_task():
    """Process pending outbox events and deliver them to Couche B."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    from backend.couche_a.models import OutboxEvent, OutboxStatus
    from backend.system.db import async_session_factory

    async def _inner():
        async with async_session_factory() as db:
            stmt = select(OutboxEvent).where(OutboxEvent.status == OutboxStatus.pending).limit(50)
            events = (await db.execute(stmt)).scalars().all()
            for event in events:
                try:
                    # TODO: deliver to Couche B market signal endpoint
                    event.status = OutboxStatus.delivered
                    event.delivered_at = datetime.now(timezone.utc)
                except Exception:
                    event.status = OutboxStatus.failed
            await db.commit()
            return len(events)

    return _run_async(_inner())
