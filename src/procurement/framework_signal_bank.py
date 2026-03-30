"""
M12 V6 L1 — Framework Signal Bank.

Loads weighted signals from YAML config and scores documents against known frameworks.
Extensible: adding a framework = adding a YAML section, zero code change.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.procurement.document_ontology import ProcurementFramework

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

WEIGHT_TIERS: dict[str, int] = {"strong": 5, "medium": 2, "weak": 1}


@dataclass(frozen=True, slots=True)
class WeightedSignal:
    pattern: re.Pattern[str]
    raw_text: str
    weight: int
    tier: str

    def matches(self, text: str) -> bool:
        return self.pattern.search(text) is not None


@dataclass(frozen=True, slots=True)
class FrameworkDecision:
    framework: ProcurementFramework
    confidence: float
    evidence: list[str]
    all_scores: dict[str, float]


def _compile_signal(raw: str, weight: int, tier: str) -> WeightedSignal:
    return WeightedSignal(
        pattern=re.compile(re.escape(raw), re.IGNORECASE),
        raw_text=raw,
        weight=weight,
        tier=tier,
    )


def _fw_str_to_enum(key: str) -> ProcurementFramework | None:
    try:
        return ProcurementFramework(key)
    except ValueError:
        return None


class FrameworkSignalBank:
    """Banque de signaux par framework — chargée depuis config YAML."""

    def __init__(
        self,
        signals_path: Path | None = None,
        thresholds_path: Path | None = None,
    ) -> None:
        self._signals_path = signals_path or (_CONFIG_DIR / "framework_signals.yaml")
        self._thresholds_path = thresholds_path or (
            _CONFIG_DIR / "framework_thresholds.yaml"
        )
        self.signals: dict[ProcurementFramework, list[WeightedSignal]] = {}
        self.min_confident_score: int = 5
        self.min_delta: int = 3
        self.confidence_floor: float = 0.50
        self.confidence_divisor: float = 20.0
        self.confidence_cap: float = 0.95
        self._load()

    def _load(self) -> None:
        raw_signals = self._load_yaml(self._signals_path)
        raw_thresholds = self._load_yaml(self._thresholds_path)

        weights = raw_thresholds.get("weights", WEIGHT_TIERS)
        self.min_confident_score = int(raw_thresholds.get("min_confident_score", 5))
        self.min_delta = int(raw_thresholds.get("min_delta_for_decision", 3))
        self.confidence_floor = float(raw_thresholds.get("confidence_floor", 0.50))
        self.confidence_divisor = float(raw_thresholds.get("confidence_divisor", 20.0))
        self.confidence_cap = float(raw_thresholds.get("confidence_cap", 0.95))

        for fw_key, tiers in raw_signals.items():
            fw_enum = _fw_str_to_enum(fw_key)
            if fw_enum is None:
                logger.warning("Unknown framework key in config: %s", fw_key)
                continue
            if not isinstance(tiers, dict):
                continue
            signals: list[WeightedSignal] = []
            for tier_name, patterns in tiers.items():
                w = weights.get(tier_name, 1)
                if not isinstance(patterns, list):
                    continue
                for p in patterns:
                    if isinstance(p, str) and p.strip():
                        signals.append(_compile_signal(p.strip(), w, tier_name))
            self.signals[fw_enum] = signals

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.is_file():
            logger.warning("Config YAML not found: %s", path)
            return {}
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}

    def score_document(self, text: str) -> dict[ProcurementFramework, float]:
        """Score each known framework against the full document text."""
        scores: dict[ProcurementFramework, float] = {}
        text_lower = text.lower()
        for fw, signals in self.signals.items():
            total = 0.0
            for s in signals:
                if s.pattern.search(text_lower) is not None:
                    total += s.weight
            scores[fw] = total
        return scores

    def decide(self, scores: dict[ProcurementFramework, float]) -> FrameworkDecision:
        """Framework decision with delta minimum and calibrated confidence."""
        if not scores:
            return FrameworkDecision(
                ProcurementFramework.UNKNOWN, 0.30, ["no_signals"], {}
            )

        sorted_fw = sorted(scores.items(), key=lambda x: -x[1])
        winner_fw, winner_score = sorted_fw[0]

        if winner_score < self.min_confident_score:
            return FrameworkDecision(
                ProcurementFramework.UNKNOWN,
                0.30,
                [f"winner={winner_fw.value}({winner_score}) below threshold"],
                {k.value: v for k, v in scores.items()},
            )

        if len(sorted_fw) > 1:
            runner_fw, runner_score = sorted_fw[1]
            delta = winner_score - runner_score
            if delta < self.min_delta:
                return FrameworkDecision(
                    ProcurementFramework.MIXED,
                    0.50,
                    [
                        f"{winner_fw.value}={winner_score}",
                        f"{runner_fw.value}={runner_score}",
                        f"delta={delta}",
                    ],
                    {k.value: v for k, v in scores.items()},
                )

        confidence = min(
            self.confidence_cap,
            self.confidence_floor + (winner_score / self.confidence_divisor),
        )
        evidence = [f"{winner_fw.value}={winner_score}"]
        return FrameworkDecision(
            winner_fw,
            confidence,
            evidence,
            {k.value: v for k, v in scores.items()},
        )

    def detect_framework(self, text: str) -> FrameworkDecision:
        """Full pipeline: score then decide."""
        scores = self.score_document(text)
        return self.decide(scores)
