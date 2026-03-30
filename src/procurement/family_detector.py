"""
M12 V6 L2 — Procurement Family Detector.

Detects procurement family (goods/services/works/consultancy) using signal bank
+ optional connection to the Couche B procurement dictionary.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.procurement.document_ontology import (
    ProcurementFamily,
    ProcurementFamilySub,
)

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


@dataclass(frozen=True, slots=True)
class FamilyDecision:
    family: ProcurementFamily
    family_sub: ProcurementFamilySub
    confidence: float
    evidence: list[str]
    all_scores: dict[str, float]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _score_patterns(text_lower: str, patterns: list[str]) -> float:
    hits = 0
    for p in patterns:
        if re.search(re.escape(p.lower()), text_lower):
            hits += 1
    return float(hits)


class FamilyDetector:
    """Detects procurement family from document text and optional dictionary."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or (
            _CONFIG_DIR / "procurement_family_signals.yaml"
        )
        self._signals: dict[str, dict[str, list[str]]] = {}
        self._sub_signals: dict[str, list[str]] = {}
        self._min_score: float = 3.0
        self._min_delta: float = 2.0
        self._weights: dict[str, int] = {"strong": 5, "medium": 2, "weak": 1}
        self._load()

    def _load(self) -> None:
        raw = _load_yaml(self._config_path)
        self._min_score = float(raw.get("min_confident_score", 3))
        self._min_delta = float(raw.get("min_delta_for_decision", 2))

        main_families = {"goods", "services", "works", "consultancy"}
        for fam in main_families:
            fam_data = raw.get(fam, {})
            if isinstance(fam_data, dict):
                self._signals[fam] = {
                    tier: patterns
                    for tier, patterns in fam_data.items()
                    if isinstance(patterns, list)
                }

        sub_raw = raw.get("sub_families", {})
        if isinstance(sub_raw, dict):
            for sub_key, patterns in sub_raw.items():
                if isinstance(patterns, list):
                    self._sub_signals[sub_key] = patterns

    def _score_family(self, text_lower: str, family: str) -> float:
        tiers = self._signals.get(family, {})
        total = 0.0
        for tier_name, patterns in tiers.items():
            w = self._weights.get(tier_name, 1)
            for p in patterns:
                if isinstance(p, str) and re.search(re.escape(p.lower()), text_lower):
                    total += w
        return total

    def _detect_sub_family(
        self, text_lower: str, family: ProcurementFamily
    ) -> ProcurementFamilySub:
        best_sub = ProcurementFamilySub.GENERIC
        best_hits = 0
        for sub_key, patterns in self._sub_signals.items():
            hits = sum(
                1
                for p in patterns
                if isinstance(p, str) and re.search(re.escape(p.lower()), text_lower)
            )
            if hits > best_hits:
                best_hits = hits
                try:
                    best_sub = ProcurementFamilySub(sub_key)
                except ValueError:
                    best_sub = ProcurementFamilySub.OTHER
        return best_sub

    def detect_family(self, text: str) -> FamilyDecision:
        """Full pipeline: score families, decide, detect sub-family."""
        text_lower = text.lower()
        scores: dict[str, float] = {}
        for fam in ("goods", "services", "works", "consultancy"):
            scores[fam] = self._score_family(text_lower, fam)

        sorted_fams = sorted(scores.items(), key=lambda x: -x[1])
        winner_key, winner_score = sorted_fams[0]

        if winner_score < self._min_score:
            return FamilyDecision(
                ProcurementFamily.UNKNOWN,
                ProcurementFamilySub.GENERIC,
                0.30,
                [f"all_below_threshold({self._min_score})"],
                scores,
            )

        if len(sorted_fams) > 1:
            _, runner_score = sorted_fams[1]
            delta = winner_score - runner_score
            if delta < self._min_delta:
                return FamilyDecision(
                    ProcurementFamily.MIXED,
                    ProcurementFamilySub.GENERIC,
                    0.50,
                    [
                        f"{sorted_fams[0][0]}={winner_score}",
                        f"{sorted_fams[1][0]}={runner_score}",
                    ],
                    scores,
                )

        try:
            family = ProcurementFamily(winner_key)
        except ValueError:
            family = ProcurementFamily.UNKNOWN

        confidence = min(0.95, 0.50 + (winner_score / 20.0))
        sub = self._detect_sub_family(text_lower, family)
        evidence = [f"{winner_key}={winner_score}"]

        return FamilyDecision(family, sub, confidence, evidence, scores)
