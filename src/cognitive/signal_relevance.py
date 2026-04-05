"""SignalRelevance — score de pertinence (SPEC BLOC5 B.5, simplifié)."""

from __future__ import annotations

import math


def compute_relevance_score(
    *,
    context_match: float,
    age_months: float,
    data_points: float,
    threshold_min: float,
    already_seen_within_24h: bool,
) -> float:
    """
    relevance_score = context_match * 0.45 + recency * 0.30 + confidence * 0.25
    recency = exp(-age_months/6)
    confidence = min(1.0, data_points / threshold_min) si threshold_min > 0 else 0.0
    """
    if already_seen_within_24h:
        return 0.0
    recency = math.exp(-age_months / 6.0)
    conf = min(1.0, data_points / threshold_min) if threshold_min > 0 else 0.0
    return float(context_match * 0.45 + recency * 0.30 + conf * 0.25)
