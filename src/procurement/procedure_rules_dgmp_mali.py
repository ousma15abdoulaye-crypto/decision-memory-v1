"""
M12 V6 — DGMP Mali Procurement Rules.

Direction Générale des Marchés Publics (Mali) framework-specific rules.
Read-only — uses parsed DGMP rules (existing asset).
"""

from __future__ import annotations

from dataclasses import dataclass

_DGMP_THRESHOLDS_FCFA: list[tuple[float, str, str]] = [
    (5_000_000.0, "demande_cotation", "Demande de cotation (< 5M FCFA)"),
    (25_000_000.0, "consultation_restreinte", "Consultation restreinte (5M-25M FCFA)"),
    (100_000_000.0, "appel_offres_national", "Appel d'offres national (25M-100M FCFA)"),
    (
        500_000_000.0,
        "appel_offres_national_ouvert",
        "AO national ouvert (100M-500M FCFA)",
    ),
    (float("inf"), "appel_offres_international", "AO international (> 500M FCFA)"),
]


@dataclass(frozen=True, slots=True)
class DGMPThresholdResult:
    estimated_value: float | None
    currency: str | None
    procedure_tier: str
    procedure_description: str
    confidence: float


def determine_dgmp_procedure_tier(
    estimated_value: float | None,
    currency: str | None,
) -> DGMPThresholdResult:
    """Determine DGMP Mali procedure tier from estimated value."""
    if estimated_value is None or estimated_value <= 0:
        return DGMPThresholdResult(
            estimated_value=estimated_value,
            currency=currency,
            procedure_tier="unknown",
            procedure_description="No value detected",
            confidence=0.30,
        )

    for threshold, tier, desc in _DGMP_THRESHOLDS_FCFA:
        if estimated_value <= threshold:
            return DGMPThresholdResult(
                estimated_value=estimated_value,
                currency=currency,
                procedure_tier=tier,
                procedure_description=desc,
                confidence=0.80,
            )

    return DGMPThresholdResult(
        estimated_value=estimated_value,
        currency=currency,
        procedure_tier="unknown",
        procedure_description="Above all thresholds",
        confidence=0.50,
    )


DGMP_ADMIN_REQUIRED_DOCS: frozenset[str] = frozenset(
    {
        "nif",
        "rccm",
        "rib",
        "quitus_fiscal",
        "cert_non_faillite",
        "attestation_cotisation_sociale",
    }
)

DGMP_PUBLICATION_RULES: dict[str, str] = {
    "demande_cotation": "Pas de publication obligatoire",
    "consultation_restreinte": "Lettre d'invitation",
    "appel_offres_national": "Journal national + ARMDS",
    "appel_offres_national_ouvert": "Journal national + ARMDS + DGMP",
    "appel_offres_international": "Journal national + international + DGMP + ARMDS",
}
