"""Circuit Breaker Mistral Small → Large — Canon V5.1.0 Section 7.9.

CLOSED    -> Mistral Small (primary)
OPEN      -> Mistral Large (fallback)
HALF_OPEN -> Mistral Large + test recovery

Seuils : 3 échecs en 60s -> OPEN. Recovery après 60s -> HALF_OPEN.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import StrEnum


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


PRIMARY_MODEL = "mistral-small-latest"
FALLBACK_MODEL = "mistral-large-latest"

FAILURE_THRESHOLD = 3
FAILURE_WINDOW_SECONDS = 60
RECOVERY_TIMEOUT_SECONDS = 60


@dataclass
class CircuitBreaker:
    state: BreakerState = BreakerState.CLOSED
    failures: list[float] = field(default_factory=list)
    last_failure_time: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def _clean_old_failures(self) -> None:
        now = time.time()
        self.failures = [t for t in self.failures if now - t < FAILURE_WINDOW_SECONDS]

    async def record_failure(self) -> None:
        async with self._lock:
            now = time.time()
            self.failures.append(now)
            self.last_failure_time = now
            self._clean_old_failures()

            if len(self.failures) >= FAILURE_THRESHOLD:
                self.state = BreakerState.OPEN

    async def record_success(self) -> None:
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.CLOSED
                self.failures.clear()

    async def get_state(self) -> BreakerState:
        async with self._lock:
            if self.state == BreakerState.OPEN:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= RECOVERY_TIMEOUT_SECONDS:
                    self.state = BreakerState.HALF_OPEN
            return self.state


_breaker = CircuitBreaker()


async def get_model_with_breaker() -> str:
    """Retourne le modèle à utiliser selon l'état du circuit breaker.

    CLOSED    -> Mistral Small (primary)
    OPEN      -> Mistral Large (fallback)
    HALF_OPEN -> Mistral Large (test recovery)
    """
    state = await _breaker.get_state()

    if state == BreakerState.CLOSED:
        return PRIMARY_MODEL
    return FALLBACK_MODEL


def get_breaker() -> CircuitBreaker:
    """Accès au singleton pour tests et monitoring."""
    return _breaker
