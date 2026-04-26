"""ARQ worker settings — production-wired (GAP-5, ADR-H2-ARQ-001).

To launch the worker:
    arq src.workers.arq_config.WorkerSettings

Environment:
    REDIS_URL : Redis DSN (same instance as slowapi rate-limiter)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from arq.connections import RedisSettings
except ImportError:
    RedisSettings = None  # type: ignore[assignment,misc]

from src.workers.arq_projector_couche_b import project_workspace_events_to_couche_b
from src.workers.arq_sealed_workspace import project_sealed_workspace
from src.workers.arq_tasks import (
    detect_patterns,
    generate_candidate_rules,
    index_event,
    rehydrate_bundle_document_raw_text_task,
    run_pass_minus_1,
)


async def arq_worker_on_startup(ctx: dict) -> None:
    """Vérifie R2 si configuré ; sinon assure ``UPLOADS_DIR`` (repli filesystem)."""
    from src.core.config import get_settings, make_r2_s3_client

    s = get_settings()
    if s.r2_object_storage_configured():
        try:
            client = make_r2_s3_client()
            client.head_bucket(Bucket=s.R2_BUCKET_NAME)
            logger.info("[ARQ] R2 bucket accessible : %s", s.R2_BUCKET_NAME)
        except Exception as exc:
            logger.error("[ARQ] R2 inaccessible : %s", exc)
            raise
    else:
        try:
            root = Path(s.UPLOADS_DIR)
            root.mkdir(parents=True, exist_ok=True)
            logger.info(
                "[ARQ] UPLOADS_DIR (Pass-1, repli sans R2) : %s", root.resolve()
            )
        except OSError as exc:
            logger.warning("[ARQ] Création UPLOADS_DIR impossible : %s", exc)


@dataclass(frozen=True)
class ArqSettings:
    redis_url: str
    max_jobs: int = 10
    job_timeout: int = 300


def get_arq_settings() -> ArqSettings:
    return ArqSettings(redis_url=os.environ.get("REDIS_URL", ""))


def _make_redis_settings() -> RedisSettings | None:
    if RedisSettings is None:
        return None
    url = os.environ.get("REDIS_URL", "")
    if not url:
        return None
    try:
        return RedisSettings.from_dsn(url)
    except Exception:
        return None


class WorkerSettings:
    """ARQ WorkerSettings — consumed by `arq src.workers.arq_config.WorkerSettings`."""

    on_startup = arq_worker_on_startup
    functions = [
        index_event,
        detect_patterns,
        generate_candidate_rules,
        rehydrate_bundle_document_raw_text_task,
        run_pass_minus_1,
        project_workspace_events_to_couche_b,
        project_sealed_workspace,
    ]
    max_jobs = 10
    job_timeout = 300
    keep_result = 300

    redis_settings = _make_redis_settings()
