"""
Test : Market Signal sans impact sur les scores
Gate : 🔴 BLOQUANT CI (actif dès M-SCORING-ENGINE)
ADR  : ADR-0002 §2.2
REF  : §7 Constitution V3.3.2
"""
import pytest


@pytest.mark.skip(
    reason="À implémenter dans M-SCORING-ENGINE. "
           "🔴 BLOQUE CI quand actif."
)
def test_market_signal_has_zero_impact_on_supplier_scores():
    """
    Modifier le Market Signal ne doit pas modifier
    supplier_scores.weighted_total.
    §7 : La Couche B est strictement read-only vis-à-vis de A.
    """
    pass
