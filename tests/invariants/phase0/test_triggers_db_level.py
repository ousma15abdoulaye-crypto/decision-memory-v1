"""
Test : Triggers PostgreSQL niveau DB
Gate : 🔴 BLOQUANT CI (actif dès M-EXTRACTION-CORRECTIONS)
ADR  : ADR-0002 §2.6
INV  : INV-6
"""
import pytest


@pytest.mark.db_integrity
@pytest.mark.skip(
    reason="À implémenter dans M-EXTRACTION-CORRECTIONS. "
           "Test direct psycopg2 — bypass API."
)
def test_trigger_blocks_update_on_corrections_directly(db_conn):
    """
    Test du trigger enforce_corrections_append_only
    directement via connexion psycopg2 raw (bypass API).
    🔴 BLOQUE CI quand actif.
    """
    pass


@pytest.mark.db_integrity
@pytest.mark.skip(
    reason="À implémenter dans M-EXTRACTION-CORRECTIONS."
)
def test_trigger_blocks_delete_on_corrections_directly(db_conn):
    """Trigger doit bloquer DELETE direct via psycopg2."""
    pass
