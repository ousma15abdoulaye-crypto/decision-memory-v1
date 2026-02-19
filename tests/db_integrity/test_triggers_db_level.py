"""
Tests : Triggers PostgreSQL — intégrité DB niveau bas
Gate  : 🔴 BLOQUANT CI (actif dès M-EXTRACTION-CORRECTIONS)
ADR   : ADR-0002 §2.6
INV   : INV-6
"""
import pytest


@pytest.mark.db_integrity
@pytest.mark.skip(
    reason="À implémenter dans M-EXTRACTION-CORRECTIONS. "
           "Connexion psycopg2 raw requise (fixture db_conn). "
           "Tester le trigger enforce_corrections_append_only."
)
def test_trigger_enforce_corrections_append_only_blocks_update(db_conn):
    """
    UPDATE direct sur extraction_corrections via psycopg2
    doit lever une exception avec message 'append-only' ou 'INV-6'.
    🔴 BLOQUE CI quand actif.
    """
    pass


@pytest.mark.db_integrity
@pytest.mark.skip(
    reason="À implémenter dans M-EXTRACTION-CORRECTIONS."
)
def test_trigger_enforce_corrections_append_only_blocks_delete(db_conn):
    """DELETE direct doit lever une exception."""
    pass
