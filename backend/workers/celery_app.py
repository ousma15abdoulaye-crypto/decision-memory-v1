"""Celery application configuration."""

from __future__ import annotations

from celery import Celery

from backend.system.settings import get_settings

__all__ = ["celery_app"]

settings = get_settings()

celery_app = Celery(
    "dms_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
