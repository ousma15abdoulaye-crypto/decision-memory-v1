"""Tests — ARQ placeholder tasks."""

from __future__ import annotations

import asyncio

from src.workers.arq_tasks import (
    detect_patterns,
    generate_candidate_rules,
    index_event,
)


class TestIndexEvent:
    def test_returns_indexed(self) -> None:
        result = asyncio.get_event_loop().run_until_complete(
            index_event({}, {"event_type": "test"})
        )
        assert result == "indexed"


class TestDetectPatterns:
    def test_returns_zero(self) -> None:
        result = asyncio.get_event_loop().run_until_complete(detect_patterns({}))
        assert result == 0


class TestGenerateCandidateRules:
    def test_returns_zero(self) -> None:
        result = asyncio.get_event_loop().run_until_complete(
            generate_candidate_rules({})
        )
        assert result == 0
