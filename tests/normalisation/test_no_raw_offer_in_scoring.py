"""
Test : Aucune offre brute dans le scoring
Gate : 🔴 BLOQUANT CI (actif dès M-NORMALISATION-ITEMS)
ADR  : ADR-0001 §2.4 + ADR-0002
INV  : INV-2 (primauté Couche A)
"""
import pytest


@pytest.mark.skip(
    reason="À implémenter dans M-NORMALISATION-ITEMS. "
           "Vérifier que le ScoringEngine lève une erreur "
           "si des offres non normalisées lui sont passées. "
           "🔴 BLOQUE CI quand actif."
)
def test_scoring_engine_rejects_raw_offers():
    """
    Le ScoringEngine doit lever RawOfferError (ou équivalent)
    si normalized_line_items est vide ou absent pour un supplier.
    🔴 BLOQUE CI quand actif.
    """
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-NORMALISATION-ITEMS."
)
def test_offers_must_pass_through_normalisation():
    """
    Toutes les offres doivent avoir requires_human_review=False
    ou reviewed_at non null avant d'entrer dans le scoring.
    """
    pass
