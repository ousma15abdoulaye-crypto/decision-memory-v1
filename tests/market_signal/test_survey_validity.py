"""
Tests : Règles Market Survey terrain Sahel (SR-1 à SR-7)
Gate  : 🔴 BLOQUANT CI (actif dès M-MARKET-SURVEY-WORKFLOW)
ADR   : ADR-0002 §2.3
"""

import pytest


@pytest.mark.skip(
    reason="À implémenter dans M-MARKET-SURVEY-WORKFLOW. 🔴 BLOQUE CI quand actif."
)
def test_sr1_minimum_3_cotations_per_item():
    """
    SR-1 : Un survey avec moins de 3 cotations par item
    ne peut pas être validé.
    """
    pass


@pytest.mark.skip(reason="À implémenter dans M-MARKET-SURVEY-WORKFLOW.")
def test_sr2_zone_geographique_obligatoire():
    """SR-2 : Zone géographique obligatoire à la saisie."""
    pass


@pytest.mark.skip(reason="À implémenter dans M-MARKET-SURVEY-WORKFLOW.")
def test_sr3_survey_expired_after_90_days():
    """
    SR-3 : Un survey de plus de 90 jours doit être
    marqué 'expired' et non utilisable dans Market Signal.
    """
    pass


@pytest.mark.skip(reason="À implémenter dans M-MARKET-SURVEY-WORKFLOW.")
def test_sr5_validation_requires_authorized_role():
    """
    SR-5 : Seul un utilisateur avec rôle buyer ou admin
    peut passer un survey en 'validated'.
    RBAC requis.
    """
    pass
