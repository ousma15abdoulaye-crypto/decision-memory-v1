"""
Signaux visuels M16 — source unique (F6).

Seuils alignés sur ``regime_from_overall`` / confidence_envelope (0.80 / 0.50).
"""

from __future__ import annotations

from typing import Any

from src.cognitive.confidence_envelope import regime_from_overall
from src.models.m16_enums import PriceSignal


def _numeric_from_cell(cell_json: dict[str, Any]) -> float | None:
    if not isinstance(cell_json, dict):
        return None
    for key in ("score", "numeric_score", "value"):
        v = cell_json.get(key)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def compute_assessment_signal(
    *,
    confidence: float | None = None,
    assessment_status: str = "draft",
    open_clarifications: int = 0,
) -> str:
    """Signal pour une cellule CriterionAssessment."""
    if open_clarifications > 0:
        return PriceSignal.bell.value

    st = (assessment_status or "").lower()
    if st in ("contested", "non_conformant"):
        return PriceSignal.red.value
    if st in ("not_applicable",):
        return PriceSignal.yellow.value

    if confidence is None:
        return PriceSignal.yellow.value

    reg = regime_from_overall(float(confidence))
    if reg == "green":
        return PriceSignal.green.value
    if reg == "yellow":
        return PriceSignal.yellow.value
    return PriceSignal.red.value


def compute_price_signal(
    *,
    market_delta_pct: float | None = None,
    extraction_confidence: float | None = None,
    open_clarifications: int = 0,
) -> str:
    """Signal pour une ligne prix (projection comparatif)."""
    if open_clarifications > 0:
        return PriceSignal.bell.value

    if extraction_confidence is not None and float(extraction_confidence) < 0.5:
        return PriceSignal.red.value

    if market_delta_pct is None:
        return PriceSignal.yellow.value

    d = abs(float(market_delta_pct))
    if d < 0.15:
        return PriceSignal.green.value
    if d < 0.30:
        return PriceSignal.yellow.value
    return PriceSignal.bell.value


def compute_domain_signal(criteria_signals: list[str]) -> str:
    """Le pire signal l'emporte."""
    if not criteria_signals:
        return PriceSignal.yellow.value

    priority = {
        PriceSignal.red.value: 0,
        PriceSignal.bell.value: 1,
        PriceSignal.yellow.value: 2,
        PriceSignal.green.value: 3,
    }
    worst = min(criteria_signals, key=lambda s: priority.get(s, 99))
    return worst


def signal_for_criterion_assessment_row(
    row: dict[str, Any],
    *,
    open_clarifications: int = 0,
) -> str:
    """À partir d'une ligne ``criterion_assessments`` (dict DB)."""
    cj = row.get("cell_json")
    if not isinstance(cj, dict):
        cj = {}
    return compute_assessment_signal(
        confidence=row.get("confidence"),
        assessment_status=str(row.get("assessment_status") or "draft"),
        open_clarifications=open_clarifications,
    )
