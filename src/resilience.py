"""Resilience patterns: retry & circuit breaker (M4D)."""

import logging

import pybreaker
from psycopg import DatabaseError, OperationalError
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


# ============================================
# CIRCUIT BREAKER POUR CONNEXIONS DB
# ============================================


class DatabaseCircuitBreaker:
    """Circuit breaker pour pool connexions PostgreSQL."""

    def __init__(self):
        self.breaker = pybreaker.CircuitBreaker(
            fail_max=5,  # Ouvre après 5 échecs consécutifs
            reset_timeout=60,  # Réessaie après 60 secondes
            exclude=[KeyboardInterrupt],
            name="PostgreSQL Connection Pool",
        )

    def call(self, func, *args, **kwargs):
        """Exécute fonction avec circuit breaker."""
        try:
            return self.breaker.call(func, *args, **kwargs)
        except pybreaker.CircuitBreakerError:
            logger.error("[BREAKER] Circuit ouvert – trop d'échecs DB")
            raise Exception("Database temporarily unavailable (circuit breaker open)")


# Instance globale
db_breaker = DatabaseCircuitBreaker()


# ============================================
# RETRY DECORATOR POUR OPÉRATIONS DB
# ============================================

retry_db_operation = retry(
    stop=stop_after_attempt(3),  # Max 3 tentatives
    wait=wait_exponential(multiplier=1, min=1, max=10),  # Backoff exponentiel
    retry=retry_if_exception_type((OperationalError, DatabaseError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


# ============================================
# HELPERS POUR EXTRACTION LLM (FUTURE M3A)
# ============================================


class ExtractionCircuitBreaker:
    """Circuit breaker pour appels LLM extraction."""

    def __init__(self):
        self.breaker = pybreaker.CircuitBreaker(
            fail_max=3, reset_timeout=30, name="LLM Extraction"  # Ouvre après 3 échecs  # Réessaie après 30 secondes
        )

    def call(self, func, *args, **kwargs):
        """Exécute extraction avec protection."""
        try:
            return self.breaker.call(func, *args, **kwargs)
        except pybreaker.CircuitBreakerError:
            logger.error("[BREAKER] LLM extraction circuit ouvert")
            raise Exception("Extraction service temporarily unavailable")


extraction_breaker = ExtractionCircuitBreaker()


@retry(
    stop=stop_after_attempt(2),  # 2 tentatives seulement (LLM coûteux)
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(Exception),  # Toutes exceptions
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def retry_llm_call(func, *args, **kwargs):
    """Wrapper retry pour appels LLM."""
    return extraction_breaker.call(func, *args, **kwargs)
