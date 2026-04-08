"""Tests Circuit Breaker — Canon V5.1.0 Section 7.9, Locking test 13.

Vérifie les transitions CLOSED -> OPEN -> HALF_OPEN -> CLOSED.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

from src.agent.circuit_breaker import (
    FALLBACK_MODEL,
    PRIMARY_MODEL,
    BreakerState,
    CircuitBreaker,
    get_model_with_breaker,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestCircuitBreakerStates:
    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        assert cb.state == BreakerState.CLOSED

    def test_stays_closed_under_threshold(self):
        cb = CircuitBreaker()
        _run(cb.record_failure())
        _run(cb.record_failure())
        assert cb.state == BreakerState.CLOSED

    def test_opens_at_threshold(self):
        cb = CircuitBreaker()
        _run(cb.record_failure())
        _run(cb.record_failure())
        _run(cb.record_failure())
        assert cb.state == BreakerState.OPEN

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker()
        _run(cb.record_failure())
        _run(cb.record_failure())
        _run(cb.record_failure())
        assert cb.state == BreakerState.OPEN

        cb.last_failure_time = time.time() - 61
        state = _run(cb.get_state())
        assert state == BreakerState.HALF_OPEN

    def test_closes_after_success_in_half_open(self):
        cb = CircuitBreaker()
        cb.state = BreakerState.HALF_OPEN
        _run(cb.record_success())
        assert cb.state == BreakerState.CLOSED
        assert len(cb.failures) == 0


class TestGetModelWithBreaker:
    def test_closed_returns_primary(self):
        async def _fake_closed():
            return BreakerState.CLOSED

        with patch("src.agent.circuit_breaker._breaker") as mock_b:
            mock_b.get_state = _fake_closed
            model = _run(get_model_with_breaker())
        assert model == PRIMARY_MODEL

    def test_open_returns_fallback(self):
        async def _fake_open():
            return BreakerState.OPEN

        with patch("src.agent.circuit_breaker._breaker") as mock_b:
            mock_b.get_state = _fake_open
            model = _run(get_model_with_breaker())
        assert model == FALLBACK_MODEL
