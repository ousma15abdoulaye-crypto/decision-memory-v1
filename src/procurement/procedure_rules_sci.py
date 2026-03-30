"""
M12 V6 — SCI Procurement Rules.

Save the Children International procurement framework-specific rules and signals.
Read-only — uses parsed SCI rules (existing asset).
"""

from __future__ import annotations

from dataclasses import dataclass

_SCI_THRESHOLDS: list[tuple[float, str, str]] = [
    (5_000.0, "micro_purchase", "1 quotation minimum"),
    (25_000.0, "small_purchase", "3 quotations minimum"),
    (100_000.0, "formal_rfq", "Formal RFQ process"),
    (250_000.0, "formal_itt", "Formal ITT/DAO"),
    (float("inf"), "international_tender", "International competitive bidding"),
]


@dataclass(frozen=True, slots=True)
class SCIThresholdResult:
    estimated_value: float | None
    currency: str | None
    procedure_tier: str
    procedure_description: str
    confidence: float


def determine_sci_procedure_tier(
    estimated_value: float | None,
    currency: str | None,
) -> SCIThresholdResult:
    """Determine SCI procurement procedure tier from estimated value."""
    if estimated_value is None or estimated_value <= 0:
        return SCIThresholdResult(
            estimated_value=estimated_value,
            currency=currency,
            procedure_tier="unknown",
            procedure_description="No value detected",
            confidence=0.30,
        )

    for threshold, tier, desc in _SCI_THRESHOLDS:
        if estimated_value <= threshold:
            return SCIThresholdResult(
                estimated_value=estimated_value,
                currency=currency,
                procedure_tier=tier,
                procedure_description=desc,
                confidence=0.80,
            )

    return SCIThresholdResult(
        estimated_value=estimated_value,
        currency=currency,
        procedure_tier="unknown",
        procedure_description="Above all thresholds",
        confidence=0.50,
    )


SCI_ADMIN_REQUIRED_DOCS: frozenset[str] = frozenset(
    {
        "nif",
        "rccm",
        "rib",
        "quitus_fiscal",
        "sci_conditions_signed",
        "sanctions_declaration",
    }
)

SCI_EVALUATION_CRITERIA_TEMPLATE: dict[str, float] = {
    "technical": 70.0,
    "financial": 30.0,
}
