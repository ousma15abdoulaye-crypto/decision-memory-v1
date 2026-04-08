"""Fondation cognitive V4.3.1 — domaine pur (SPEC BLOC5)."""

from src.cognitive.cognitive_state import (
    CognitiveFacts,
    CognitiveStateResult,
    TransitionForbidden,
    compute_cognitive_state,
    compute_cognitive_state_result,
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
    "CognitiveStateResult",
    "TransitionForbidden",
    "compute_cognitive_state",
    "compute_cognitive_state_result",
    "ConfidenceEnvelope",
    "compute_bundle_confidence",
    "compute_frame_confidence",
    "regime_from_overall",
    "compute_relevance_score",
]
