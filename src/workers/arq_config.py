"""ARQ worker settings (Redis URL from environment)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ArqSettings:
    redis_url: str
    max_jobs: int = 10
    job_timeout: int = 300


def get_arq_settings() -> ArqSettings:
    return ArqSettings(redis_url=os.environ.get("REDIS_URL", ""))
