"""
Test : Scores indépendants de la Couche B
Gate : 🔴 BLOQUANT CI (actif dès M-SCORING-ENGINE)
ADR  : ADR-0002 §2.4
INV  : INV-3 + §7 Constitution
"""
import pytest


@pytest.mark.skip(
    reason="À implémenter dans M-SCORING-ENGINE. "
           "Vérifier que le score calculé est identique "
           "qu'un Market Signal soit disponible ou non. "
           "🔴 BLOQUE CI quand actif."
)
def test_score_identical_with_and_without_market_signal():
    """
    Le score d'un fournisseur ne doit pas changer
    selon que le Market Signal est disponible ou non.
    INV-3 : Couche B non prescriptive.
    🔴 BLOQUE CI quand actif.
    """
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-SCORING-ENGINE."
)
def test_scoring_engine_output_has_no_recommendation():
    """
    L'output du ScoringEngine ne doit contenir
    aucun champ 'recommendation', 'suggested_winner',
    'preferred_supplier' ou équivalent.
    INV-3 + §1.2 Constitution.
    """
    pass
