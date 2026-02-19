"""
Test : Import statique Couche B dans Couche A — version étendue
Gate : 🔴 BLOQUANT CI (actif dès M-SCORING-ENGINE.done)
ADR  : ADR-0002 §2.4
"""
import pytest


@pytest.mark.skip(
    reason="Actif dès M-SCORING-ENGINE.done. "
           "Version complémentaire de test_couche_a_b_boundary.py "
           "pour les cas d'imports indirects."
)
def test_scoring_module_has_no_couche_b_dependency():
    """
    Le module scoring ne doit contenir aucune dépendance
    directe ou indirecte vers Couche B.
    🔴 BLOQUE CI quand actif.
    """
    pass
