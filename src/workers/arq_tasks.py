"""ARQ background tasks for VIVANT V2 (event indexing, patterns, candidate rules).

Tasks are async; they receive an ``arq`` context dict with a db_conn factory
injected via on_startup. When arq is not installed (CI), the functions still
import cleanly — stubs are never called in production.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_conn_factory():
    """Return a conn_factory using PsycopgCursorAdapter over get_db_cursor."""
    from src.db.connection import get_db_cursor
    from src.db.cursor_adapter import PsycopgCursorAdapter

    class _CtxConn:
        """One-shot connection wrapper for service compatibility."""

        def __init__(self) -> None:
            self._cur = None
            self._ctx = None

        def _open(self):
            self._ctx = get_db_cursor()
            self._cur = PsycopgCursorAdapter(self._ctx.__enter__())
            return self._cur

    def factory():
        from src.db.connection import get_db_cursor
        from src.db.cursor_adapter import PsycopgCursorAdapter

        ctx = get_db_cursor()
        cur = ctx.__enter__()
        return PsycopgCursorAdapter(cur)

    return factory


async def index_event(ctx: dict[str, Any], event_dict: dict[str, Any]) -> str:
    """Index a single domain event into dms_event_index.

    ``event_dict`` must match the ``EventEntry`` Pydantic model fields.
    Called from bridge triggers callbacks or external producers.
    """
    try:
        from src.memory.event_index_models import EventEntry
        from src.memory.event_index_service import EventIndexService

        entry = EventEntry(**event_dict)
        svc = EventIndexService(_get_conn_factory())
        event_id = svc.append(entry)
        logger.info(
            "index_event: appended %s (domain=%s)", event_id, entry.event_domain
        )
        return event_id
    except Exception as exc:
        logger.error("index_event failed: %s", exc)
        raise


async def detect_patterns(ctx: dict[str, Any]) -> int:
    """Detect correction clusters and generate candidate rules.

    Reads ``m13_correction_log``, detects patterns with ``PatternDetector``,
    then persists candidate rules via ``CandidateRuleService``.
    Returns the count of rules saved.
    """
    try:
        from src.memory.candidate_rule_generator import CandidateRuleGenerator
        from src.memory.candidate_rule_service import CandidateRuleService
        from src.memory.pattern_detector import PatternDetector

        factory = _get_conn_factory()
        conn = factory()

        detector = PatternDetector(lambda: conn)
        patterns = detector.detect_all()
        logger.info("detect_patterns: found %d patterns", len(patterns))

        generator = CandidateRuleGenerator()
        rules = generator.generate_from_patterns(patterns)
        logger.info("detect_patterns: generated %d candidate rules", len(rules))

        svc = CandidateRuleService(lambda: conn)
        saved = 0
        for rule in rules:
            try:
                svc.save(rule)
                saved += 1
            except Exception as save_exc:
                logger.warning(
                    "detect_patterns: skip rule %s: %s", rule.get("rule_id"), save_exc
                )

        return saved
    except Exception as exc:
        logger.error("detect_patterns failed: %s", exc)
        raise


async def generate_candidate_rules(ctx: dict[str, Any]) -> int:
    """Alias for detect_patterns — kept for backward compat / independent scheduling."""
    return await detect_patterns(ctx)
