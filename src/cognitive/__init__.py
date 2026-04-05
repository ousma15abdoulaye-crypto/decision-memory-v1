"""Fondation cognitive V4.3.1 — domaine pur (SPEC BLOC5)."""

from src.cognitive.cognitive_state import (
    CognitiveFacts,
    TransitionForbidden,
    compute_cognitive_state,
)
from src.cognitive.confidence_envelope import (
    ConfidenceEnvelope,
    compute_bundle_confidence,
    compute_frame_confidence,
    regime_from_overall,
)
from src.cognitive.signal_relevance import compute_relevance_score

__all__ = [
    "CognitiveFacts",
    "TransitionForbidden",
    "compute_cognitive_state",
    "ConfidenceEnvelope",
    "compute_bundle_confidence",
    "compute_frame_confidence",
    "regime_from_overall",
    "compute_relevance_score",
]
