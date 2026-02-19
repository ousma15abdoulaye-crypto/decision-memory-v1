"""
Tests : Règles Market Signal MS-1/MS-2/MS-3 + dégradation
Gate  : 🔴 BLOQUANT CI (actif dès M-MARKET-SIGNAL-ENGINE)
ADR   : ADR-0002 §2.2
INV   : INV-3 (non prescriptif)
"""
import pytest


@pytest.mark.skip(
    reason="À implémenter dans M-MARKET-SIGNAL-ENGINE. "
           "🔴 BLOQUE CI quand actif."
)
def test_ms1_survey_terrain_has_priority(fresh_survey, history, mercuriale):
    """
    Règle MS-1 : Market Survey terrain (≤90j, ≥3 cotations)
    a la priorité maximale comme référence de prix.
    """
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-MARKET-SIGNAL-ENGINE."
)
def test_ms2_history_used_when_no_fresh_survey(history, mercuriale):
    """
    Règle MS-2 : Historique 24 mois utilisé
    quand MS-1 non activable.
    """
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-MARKET-SIGNAL-ENGINE."
)
def test_ms3_mercuriale_always_available(mercuriale):
    """Règle MS-3 : Mercuriale toujours disponible."""
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-MARKET-SIGNAL-ENGINE."
)
def test_ms_degrade_missing_1_source_returns_partial():
    """1 source manquante → signal_quality = 'PARTIAL' ⚠️"""
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-MARKET-SIGNAL-ENGINE."
)
def test_ms_degrade_missing_2_sources_returns_degraded():
    """2 sources manquantes → signal_quality = 'DEGRADED' 🔴"""
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-MARKET-SIGNAL-ENGINE."
)
def test_ms_zero_signal_never_writes_to_couche_a():
    """
    Règle MS-ZERO : MarketSignalEngine ne modifie jamais
    les tables Couche A (supplier_scores, criteria, etc.).
    """
    pass
