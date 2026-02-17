"""Tests resilience patterns (M4D)."""

import os
import pytest
from unittest.mock import patch, MagicMock
from psycopg import OperationalError
import pybreaker

# Set DATABASE_URL before importing src.db
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

from src.resilience import db_breaker, extraction_breaker


@pytest.fixture(autouse=True)
def reset_circuit_breakers():
    """Reset circuit breakers before each test."""
    # Reset state
    db_breaker.breaker._state = pybreaker.CircuitClosedState(db_breaker.breaker)
    extraction_breaker.breaker._state = pybreaker.CircuitClosedState(
        extraction_breaker.breaker
    )
    # Reset failure counter (accessing private attribute)
    db_breaker.breaker._state_storage._counter = 0
    extraction_breaker.breaker._state_storage._counter = 0
    # Reset opened_at timestamp
    db_breaker.breaker._state_storage.opened_at = None
    extraction_breaker.breaker._state_storage.opened_at = None
    yield
    # Reset after test as well
    db_breaker.breaker._state = pybreaker.CircuitClosedState(db_breaker.breaker)
    extraction_breaker.breaker._state = pybreaker.CircuitClosedState(
        extraction_breaker.breaker
    )
    db_breaker.breaker._state_storage._counter = 0
    extraction_breaker.breaker._state_storage._counter = 0
    db_breaker.breaker._state_storage.opened_at = None
    extraction_breaker.breaker._state_storage.opened_at = None


def test_retry_db_connection_success_after_failures():
    """Connexion réussit après 2 échecs (retry)."""
    from src.db import get_connection

    call_count = 0

    def mock_connect():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise OperationalError("Connection refused")
        # Return a proper mock with commit/rollback/close methods
        mock_conn = MagicMock()
        mock_conn.commit = MagicMock()
        mock_conn.rollback = MagicMock()
        mock_conn.close = MagicMock()
        return mock_conn

    with patch("src.db._get_raw_connection", side_effect=mock_connect):
        with get_connection() as conn:
            assert conn is not None
            assert call_count == 3  # 2 échecs + 1 succès


def test_retry_db_fails_after_max_attempts():
    """Échec définitif après 3 tentatives."""
    from src.db import get_connection

    with patch("src.db._get_raw_connection", side_effect=OperationalError("Dead")):
        with pytest.raises(OperationalError):
            with get_connection() as _:
                pass


def test_circuit_breaker_opens_after_failures():
    """Circuit breaker s'ouvre après 5 échecs consécutifs."""
    # Reset breaker
    db_breaker.breaker._state = pybreaker.CircuitClosedState(db_breaker.breaker)

    def always_fail():
        raise OperationalError("Always fails")

    # 5 échecs consécutifs
    for i in range(5):
        try:
            db_breaker.call(always_fail)
        except Exception:
            pass

    # 6e appel → circuit ouvert
    with pytest.raises(Exception, match="temporarily unavailable"):
        db_breaker.call(always_fail)


def test_extraction_breaker_protects_llm():
    """Circuit breaker extraction protège contre échecs LLM."""
    extraction_breaker.breaker._state = pybreaker.CircuitClosedState(
        extraction_breaker.breaker
    )

    def failing_extraction():
        raise Exception("LLM timeout")

    # 3 échecs → circuit ouvert
    for i in range(3):
        try:
            extraction_breaker.call(failing_extraction)
        except Exception:
            pass

    with pytest.raises(Exception, match="temporarily unavailable"):
        extraction_breaker.call(failing_extraction)


def test_logging_retry_attempts(caplog):
    """Vérifier logs retry - test direct de retry_db_operation sans circuit breaker."""
    from src.resilience import retry_db_operation
    from psycopg import OperationalError

    call_count = 0

    @retry_db_operation
    def test_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise OperationalError(f"Temporary failure {call_count}")
        return "success"

    result = test_func()

    # Vérifier que ça a réussi après retries
    assert result == "success"
    assert call_count == 3

    # Vérifier logs (tenacity log les retries automatiquement)
    # Le logger de tenacity devrait avoir logué les tentatives
    assert len(caplog.records) > 0
