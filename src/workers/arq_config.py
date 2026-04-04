"""ARQ worker settings — production-wired (GAP-5, ADR-H2-ARQ-001).

To launch the worker:
    arq src.workers.arq_config.WorkerSettings

Environment:
    REDIS_URL : Redis DSN (same instance as slowapi rate-limiter)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from arq.connections import RedisSettings
except ImportError:
    RedisSettings = None  # type: ignore[assignment,misc]

from src.workers.arq_projector_couche_b import project_workspace_events_to_couche_b
from src.workers.arq_tasks import (
    detect_patterns,
    generate_candidate_rules,
    index_event,
    run_pass_minus_1,
)


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

    functions = [
        index_event,
        detect_patterns,
        generate_candidate_rules,
        run_pass_minus_1,
        project_workspace_events_to_couche_b,
    ]
    max_jobs = 10
    job_timeout = 300
    keep_result = 300

    redis_settings = _make_redis_settings()
