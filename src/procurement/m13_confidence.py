"""
M13 — discrétisation des confiances vers la grille DMS {0.6, 0.8, 1.0}.
ADR-M13-001
"""

from __future__ import annotations

from typing import Literal

M13Confidence = Literal[0.6, 0.8, 1.0]


def m13_discretize_confidence(raw: float) -> M13Confidence:
    """Mappe une confiance brute [0,1] vers {0.6, 0.8, 1.0}."""
    if raw >= 0.9:
        return 1.0
    if raw >= 0.7:
        return 0.8
    return 0.6
