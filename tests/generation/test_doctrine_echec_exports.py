"""
Tests : Doctrine d'échec §9 — exports incomplets marqués
Gate  : 🔴 BLOQUANT CI (actif dès M-CBA-GEN + M-PV-GEN)
ADR   : ADR-0002 §2.7
REF   : §9 Constitution V3.3.2
"""
import pytest


@pytest.mark.skip(
    reason="À implémenter dans M-CBA-GEN. "
           "§9 : Exports incomplets = marqués, pas masqués. "
           "🔴 BLOQUE CI quand actif."
)
def test_incomplete_cba_returns_incomplete_status():
    """
    Un CBA généré sans scores disponibles doit retourner
    status='incomplete' avec raison explicite.
    ❌ Jamais : générer un fichier silencieusement incomplet.
    §9 Constitution V3.3.2.
    """
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-PV-GEN."
)
def test_pv_without_locked_committee_is_blocked():
    """
    Un PV ne peut pas être généré sans comité verrouillé.
    §9 : PV douteux = non générés.
    """
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-CBA-GEN."
)
def test_uncertain_items_flagged_in_cba_output():
    """
    §9 : Items à faible confiance (< 0.75) doivent être
    flaggés dans le CBA, pas masqués.
    """
    pass
