"""
M12 V6 — DGMP Mali (palier procédure depuis YAML).

Source unique : ``config/regulatory/dgmp_mali/thresholds.yaml``
(via RegulatoryConfigLoader). Anciennes constantes Python retirées.

``DGMP_ADMIN_REQUIRED_DOCS`` / ``DGMP_PUBLICATION_RULES`` : conservés pour
référence locale ; non utilisés par le moteur M13 (YAML).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.procurement.regulatory_config_loader import RegulatoryConfigLoader

_USD_TO_FCFA = 600.0
_EUR_TO_FCFA = 655.957
_FW = "dgmp_mali"


def _to_fcfa(amount: float, currency: str | None) -> float:
    if not currency:
        return amount
    c = currency.upper().strip()
    if c in ("XOF", "FCFA", "CFA"):
        return amount
    if c == "USD":
        return amount * _USD_TO_FCFA
    if c == "EUR":
        return amount * _EUR_TO_FCFA
    return amount


def _pick_tier_rows(bundle: dict[str, Any], family_key: str) -> list[dict[str, Any]]:
    """``bundle`` = ``load_framework_bundle('dgmp_mali')`` → clé ``thresholds`` = racine YAML."""
    root = bundle.get("thresholds") or {}
    if not isinstance(root, dict):
        return []
    fam = root.get(family_key) or root.get("goods") or {}
    if not isinstance(fam, dict):
        return []
    tiers = fam.get("tiers")
    return tiers if isinstance(tiers, list) else []


def _match_tier(
    amount_fcfa: float, tiers: list[dict[str, Any]]
) -> dict[str, Any] | None:
    for row in tiers:
        if not isinstance(row, dict):
            continue
        lo = float(row.get("min_value") or 0)
        hi = row.get("max_value")
        hi_f = float(hi) if hi is not None else None
        if hi_f is None:
            if amount_fcfa >= lo:
                return row
        elif lo <= amount_fcfa < hi_f:
            return row
    return None


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
    *,
    family_key: str = "goods",
) -> DGMPThresholdResult:
    """Palier DGMP Mali aligné sur ``thresholds.yaml`` (biens/services ou travaux)."""
    if estimated_value is None or estimated_value <= 0:
        return DGMPThresholdResult(
            estimated_value=estimated_value,
            currency=currency,
            procedure_tier="unknown",
            procedure_description="No value detected",
            confidence=0.30,
        )

    loader = RegulatoryConfigLoader()
    bundle = loader.load_framework_bundle(_FW)
    fcfa = _to_fcfa(float(estimated_value), currency)
    fk = "works" if family_key.lower() in ("works", "travaux") else "goods"
    tiers = _pick_tier_rows(bundle, fk)
    if not tiers:
        tiers = _pick_tier_rows(bundle, "goods")
    row = _match_tier(fcfa, tiers)
    if not row:
        return DGMPThresholdResult(
            estimated_value=estimated_value,
            currency=currency,
            procedure_tier="unknown",
            procedure_description="No YAML tier matched",
            confidence=0.50,
        )

    proc = str(row.get("procedure_required") or "unknown")
    desc = str(row.get("description") or proc)
    return DGMPThresholdResult(
        estimated_value=estimated_value,
        currency=currency,
        procedure_tier=proc,
        procedure_description=desc,
        confidence=0.80,
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

# DEPRECATED : clés historiques (pré-YAML). Préférer ``procedure_required`` du YAML.
DGMP_PUBLICATION_RULES: dict[str, str] = {
    "demande_cotation": "Pas de publication obligatoire",
    "consultation_restreinte": "Lettre d'invitation",
    "appel_offres_national": "Journal national + ARMDS",
    "appel_offres_national_ouvert": "Journal national + ARMDS + DGMP",
    "appel_offres_international": "Journal national + international + DGMP + ARMDS",
}
