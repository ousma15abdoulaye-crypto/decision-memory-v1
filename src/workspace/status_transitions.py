"""Garde-fous de transition workspace (SPEC BLOC5 C.3) — réexport."""

from src.cognitive.cognitive_state import (
    CognitiveFacts,
    TransitionForbidden,
    validate_transition,
)

__all__ = ["CognitiveFacts", "TransitionForbidden", "validate_transition"]
