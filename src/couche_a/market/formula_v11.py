"""
Formule Market Signal V1.1
ADR : docs/adr/ADR-M9-FORMULA-V1.1.md
Decideur : AO -- Abdoulaye Ousmane

IMMUABLE :
  FORMULA_VERSION, WEIGHTS, FRESHNESS,
  IQR_MULTIPLIER, ALERT_THRESHOLDS
  ne peuvent pas etre modifies sans ADR signe.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

# ── Constantes gravees ADR-M9-FORMULA-V1.1 ───────────────────────────────────

FORMULA_VERSION = "1.1"

WEIGHTS: dict[str, float] = {
    "mercuriale_official": 0.50,
    "market_survey": 0.35,
    "decision_history": 0.15,
}

FRESHNESS: dict[int, float] = {
    0: 1.00,
    1: 0.90,
    2: 0.75,
    3: 0.55,
}
FRESHNESS_OLD = 0.30
IQR_MULTIPLIER = 2.5

ALERT_THRESHOLDS: dict[str, dict] = {
    "ipc_4_emergency": {"CRITICAL": 40.0, "WATCH": 20.0},
    "ipc_5_catastrophe": {"CRITICAL": 40.0, "WATCH": 20.0},
    "ipc_3_crisis": {"WARNING": 30.0},
    "ipc_2_stressed": {"WARNING": 25.0},
    "ipc_1_minimal": {"CRITICAL": 30.0, "WARNING": 15.0},
    "normal": {"CRITICAL": 30.0, "WARNING": 15.0},
}


@dataclass
class PricePoint:
    price: float
    source_type: str
    age_months: int
    currency: str = "XOF"
    weight_override: float | None = None


@dataclass
class ContextSnapshot:
    context_type: str = "normal"
    severity_level: str = "ipc_1_minimal"
    structural_markup_pct: float = 0.0
    seasonal_deviation_pct: float = 0.0


@dataclass
class SignalResult:
    item_id: str
    zone_id: str
    formula_version: str = FORMULA_VERSION
    price_raw: float | None = None
    price_crisis_adj: float | None = None
    price_seasonal_adj: float | None = None
    residual_pct: float | None = None
    alert_level: str = "NORMAL"
    alert_message: str = ""
    signal_quality: str = "empty"
    source_mercuriale_count: int = 0
    source_survey_count: int = 0
    source_decision_count: int = 0
    structural_markup_applied: float = 0.0
    seasonal_deviation_applied: float = 0.0
    context_type_at_computation: str = "normal"
    is_propagated: bool = False
    propagated_from_zone: str | None = None
    computation_errors: list = field(default_factory=list)


class FormulaV11:
    """
    Implementation formule V1.1.
    Ne pas modifier sans ADR signe AO.
    """

    @staticmethod
    def freshness_factor(age: int) -> float:
        return FRESHNESS.get(age, FRESHNESS_OLD)

    @staticmethod
    def reject_outliers(prices: list[float]) -> list[float]:
        if len(prices) < 5:
            return prices
        q1 = statistics.quantiles(prices, n=4)[0]
        q3 = statistics.quantiles(prices, n=4)[2]
        iqr = q3 - q1
        lo = q1 - IQR_MULTIPLIER * iqr
        hi = q3 + IQR_MULTIPLIER * iqr
        return [p for p in prices if lo <= p <= hi]

    @staticmethod
    def weighted_average(
        points: list[PricePoint],
    ) -> tuple[float, float]:
        tw = 0.0
        twp = 0.0
        for pt in points:
            w = (
                pt.weight_override
                if pt.weight_override is not None
                else WEIGHTS.get(pt.source_type, 0.10)
            )
            f = FormulaV11.freshness_factor(pt.age_months)
            wf = w * f
            tw += wf
            twp += wf * pt.price
        if tw == 0:
            return 0.0, 0.0
        return twp / tw, tw

    @staticmethod
    def classify_quality(total_weight: float, n_sources: int) -> str:
        if n_sources == 0 or total_weight == 0:
            return "empty"
        if total_weight >= 0.8 and n_sources >= 3:
            return "strong"
        if total_weight >= 0.5 or n_sources >= 2:
            return "moderate"
        return "weak"

    @staticmethod
    def classify_alert(
        residual: float,
        severity: str,
    ) -> tuple[str, str]:
        t = ALERT_THRESHOLDS.get(severity, ALERT_THRESHOLDS["normal"])

        if severity in ("ipc_4_emergency", "ipc_5_catastrophe"):
            if residual > t["CRITICAL"]:
                return (
                    "CRITICAL",
                    f"Residuel {residual:.1f}% au-dessus crise {severity}",
                )
            if residual > t["WATCH"]:
                return ("WATCH", f"Ecart residuel {residual:.1f}%")
            return ("CONTEXT_NORMAL", f"Coherent {severity} documente")

        if severity == "ipc_3_crisis":
            if residual > t["WARNING"]:
                return ("WARNING", f"Ecart residuel {residual:.1f}% post-IPC3")
            return ("CONTEXT_NORMAL", "Coherent IPC3 documente")

        if severity == "ipc_2_stressed":
            if residual > t["WARNING"]:
                return ("WARNING", f"Ecart {residual:.1f}% post-saisonnalite")
            return ("SEASONAL_NORMAL", "Coherent saisonnalite IPC2")

        # IPC1 / normal
        if residual > t["CRITICAL"]:
            return ("CRITICAL", f"Anomalie {residual:.1f}% -- audit immediat")
        if residual > t["WARNING"]:
            return ("WARNING", f"Ecart {residual:.1f}% -- verifier")
        return ("NORMAL", "")

    def compute(
        self,
        item_id: str,
        zone_id: str,
        points: list[PricePoint],
        context: ContextSnapshot,
        propagated_from: str | None = None,
    ) -> SignalResult:
        r = SignalResult(
            item_id=item_id,
            zone_id=zone_id,
            context_type_at_computation=context.context_type,
            structural_markup_applied=context.structural_markup_pct,
            seasonal_deviation_applied=context.seasonal_deviation_pct,
            is_propagated=propagated_from is not None,
            propagated_from_zone=propagated_from,
        )

        if not points:
            return r

        for pt in points:
            if pt.source_type == "mercuriale_official":
                r.source_mercuriale_count += 1
            elif pt.source_type == "market_survey":
                r.source_survey_count += 1
            elif pt.source_type == "decision_history":
                r.source_decision_count += 1

        raw_prices = [pt.price for pt in points]
        cleaned = self.reject_outliers(raw_prices)
        if len(cleaned) < len(raw_prices):
            r.computation_errors.append(
                f"{len(raw_prices) - len(cleaned)} outlier(s) exclus IQR"
            )
        pts = [p for p in points if p.price in cleaned]

        price_raw, total_w = self.weighted_average(pts)
        if price_raw == 0:
            return r

        r.price_raw = round(price_raw, 4)
        r.signal_quality = self.classify_quality(total_w, len(pts))

        m = context.structural_markup_pct
        p_crisis = price_raw / (1 + m / 100) if m > 0 else price_raw
        r.price_crisis_adj = round(p_crisis, 4)

        s = context.seasonal_deviation_pct
        p_seasonal = p_crisis / (1 + s / 100) if s != 0 else p_crisis
        r.price_seasonal_adj = round(p_seasonal, 4)

        residual = ((price_raw / p_seasonal) - 1) * 100 if p_seasonal > 0 else 0.0
        r.residual_pct = round(residual, 2)

        r.alert_level, r.alert_message = self.classify_alert(
            r.residual_pct,
            context.severity_level,
        )

        if propagated_from:
            r.signal_quality = "propagated"

        return r
