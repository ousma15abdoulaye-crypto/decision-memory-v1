"""
M12 V6 L6 sub — Scoring Structure Extractor.

Extracts evaluation scoring structure from source_rules documents.
"""

from __future__ import annotations

import re
from typing import Literal

from src.procurement.procedure_models import (
    ScoringCriterionDetected,
    ScoringStructureDetected,
)

_CRITERIA_PATTERN = re.compile(
    r"(technique|financ|prix|qualit[eé]|exp[eé]rience|m[eé]thodologie"
    r"|[eé]quipe|r[eé]f[eé]rences?|qualificat|d[eé]lai|planning)"
    r"[^.]{0,80}?"
    r"(\d{1,3})\s*(?:%|points?|/\s*\d+)",
    re.IGNORECASE,
)

_THRESHOLD_PATTERN = re.compile(
    r"seuil\s+(?:technique\s+)?(?:minimum|[eé]liminatoire)?\s*(?:de\s+)?(\d{1,3})\s*(?:/\s*(\d{1,3}))?",
    re.IGNORECASE,
)

_METHOD_SIGNALS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"moins[- ]disant|lowest\s+price", re.IGNORECASE), "lowest_price"),
    (re.compile(r"mieux[- ]disant|best\s+value", re.IGNORECASE), "best_value"),
    (
        re.compile(r"qualit[eé]\s*[-/]\s*co[uû]t|quality[- ]cost", re.IGNORECASE),
        "quality_cost_based",
    ),
    (re.compile(r"budget\s+fix[eé]|fixed\s+budget", re.IGNORECASE), "fixed_budget"),
    (
        re.compile(
            r"qualification\s+du\s+consultant|consultant\s+qualification", re.IGNORECASE
        ),
        "consultant_qualification",
    ),
]


def extract_scoring_structure(text: str) -> ScoringStructureDetected:
    """Extract scoring criteria and structure from document text."""
    if not text or not text.strip():
        return ScoringStructureDetected(
            ponderation_coherence="NOT_FOUND",
            confidence=0.0,
        )

    criteria: list[ScoringCriterionDetected] = []
    total_weight = 0.0

    for m in _CRITERIA_PATTERN.finditer(text):
        name = m.group(1).strip().lower()
        weight = float(m.group(2))
        start = max(0, m.start() - 30)
        end = min(len(text), m.end() + 30)
        evidence_snippet = text[start:end].strip()

        criteria.append(
            ScoringCriterionDetected(
                criteria_name=name,
                weight_percent=weight,
                confidence=0.75,
                evidence=evidence_snippet[:200],
            )
        )
        total_weight += weight

    coherence: Literal["OK", "INCOHERENT", "INCOMPLETE", "NOT_FOUND"]
    if not criteria:
        coherence = "NOT_FOUND"
    elif 95.0 <= total_weight <= 105.0:
        coherence = "OK"
    elif total_weight > 0:
        coherence = "INCOMPLETE"
    else:
        coherence = "INCOHERENT"

    method = None
    for pat, method_name in _METHOD_SIGNALS:
        if pat.search(text):
            method = method_name
            break

    threshold = None
    threshold_match = _THRESHOLD_PATTERN.search(text)
    if threshold_match:
        num = threshold_match.group(1)
        denom = threshold_match.group(2)
        threshold = f"{num}/{denom}" if denom else f"{num}"

    confidence = 0.0
    evidence: list[str] = []
    if criteria:
        confidence = 0.70
        evidence.append(f"criteria_count={len(criteria)}")
        evidence.append(f"total_weight={total_weight}")
    if method:
        evidence.append(f"method={method}")
    if threshold:
        evidence.append(f"threshold={threshold}")

    return ScoringStructureDetected(
        criteria=criteria,
        total_weight=total_weight,
        ponderation_coherence=coherence,
        evaluation_method=method,  # type: ignore[arg-type]
        technical_threshold=threshold,
        confidence=confidence,
        evidence=evidence,
    )
