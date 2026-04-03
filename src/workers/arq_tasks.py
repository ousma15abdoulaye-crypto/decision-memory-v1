"""
ARQ background tasks for VIVANT V2 (event indexing, patterns, candidate rules).

Placeholders — wire to ``EventIndexService`` / ``PatternDetector`` when deployed.
"""

from __future__ import annotations

from typing import Any


async def index_event(ctx: dict[str, Any], event_dict: dict[str, Any]) -> str:
    """Placeholder task that would index an event."""
    _ = (ctx, event_dict)
    return "indexed"


async def detect_patterns(ctx: dict[str, Any]) -> int:
    """Placeholder task that would run pattern detection."""
    _ = ctx
    return 0


async def generate_candidate_rules(ctx: dict[str, Any]) -> int:
    """Placeholder task that would materialize candidate rules."""
    _ = ctx
    return 0
