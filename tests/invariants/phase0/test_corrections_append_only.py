"""
Test : Append-only corrections humaines
Gate : 🔴 BLOQUANT CI (actif dès M-EXTRACTION-CORRECTIONS)
ADR  : ADR-0002 §6.2
INV  : INV-6 (append-only) + INV-9 (fidélité au réel)
"""

import pytest


@pytest.mark.skip(
    reason="À implémenter dans M-EXTRACTION-CORRECTIONS. "
    "Vérifier que extraction_corrections est append-only "
    "via trigger PostgreSQL. Retirer le skip quand actif."
)
def test_corrections_cannot_be_updated():
    """
    Un UPDATE sur extraction_corrections doit lever une exception.
    Trigger : enforce_corrections_append_only
    🔴 BLOQUE CI quand actif.
    """
    pass


@pytest.mark.skip(reason="À implémenter dans M-EXTRACTION-CORRECTIONS.")
def test_corrections_cannot_be_deleted():
    """
    Un DELETE sur extraction_corrections doit lever une exception.
    """
    pass


@pytest.mark.skip(reason="À implémenter dans M-EXTRACTION-CORRECTIONS.")
def test_corrections_can_be_inserted():
    """
    Un INSERT valide doit réussir (append autorisé).
    """
    pass


@pytest.mark.skip(reason="À implémenter dans M-EXTRACTION-CORRECTIONS.")
def test_effective_view_applies_corrections_in_order():
    """
    La vue effective applique les corrections dans l'ordre
    chronologique sans modifier structured_data original.
    """
    pass
