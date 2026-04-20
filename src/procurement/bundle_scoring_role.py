"""
Runtime classification — rôle métier d'un bundle pour le scoring (Phase 1 CTO D-03).

Ne modifie pas la colonne SQL ``supplier_bundles.bundle_status`` (cycle d'assemblage
070). Enum distincte du plan directeur pour éviter collision sémantique.
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class ScoringRole(StrEnum):
    """Bundle vu par le moteur de scoring (hors état d'assemblage SQL)."""

    SCORABLE = "scorable"
    REFERENCE = "reference"
    INTERNAL = "internal"
    UNUSABLE = "unusable"


_OFFER_TYPES: frozenset[str] = frozenset(
    {"offer_technical", "offer_financial", "offer_combined"}
)
_INTERNAL_ONLY: frozenset[str] = frozenset({"rfq", "tdr", "dao"})
_REFERENCE_HEAVY: frozenset[str] = frozenset(
    {"reference_list", "cv", "licence", "submission_letter"}
)


def classify_bundle_scoring_role(
    *,
    vendor_name_raw: str,
    doc_types: frozenset[str],
) -> ScoringRole:
    """Classifie un bundle fournisseur pour inclusion dans M14 / extraction scoring.

    Heuristique conservative alignée Gate B (plan) : offre exploitable + identité
    fournisseur ; dossier source seul → INTERNAL ; pièces sans offre → UNUSABLE/REF.
    """
    docs = doc_types
    vendor = (vendor_name_raw or "").strip()
    vendor_ok = bool(vendor) and vendor.upper() != "ABSENT"
    has_offer = bool(docs & _OFFER_TYPES)

    if has_offer and vendor_ok:
        return ScoringRole.SCORABLE
    if has_offer and not vendor_ok:
        return ScoringRole.UNUSABLE
    if not docs:
        return ScoringRole.UNUSABLE
    if docs <= _INTERNAL_ONLY:
        return ScoringRole.INTERNAL
    if not has_offer and docs and docs <= (_REFERENCE_HEAVY | _INTERNAL_ONLY):
        if docs & _REFERENCE_HEAVY:
            return ScoringRole.REFERENCE
        return ScoringRole.INTERNAL
    if not has_offer:
        return ScoringRole.INTERNAL
    return ScoringRole.UNUSABLE
