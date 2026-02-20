"""
Tests : Triggers LOCK comité — niveau DB
Gate  : 🔴 BLOQUANT CI (actif dès M-COMMITTEE-CORE)
ADR   : ADR-0002 §2.6
INV   : INV-6
"""

import pytest


@pytest.mark.db_integrity
@pytest.mark.skip(
    reason="À implémenter dans M-COMMITTEE-CORE. "
    "Tester le trigger enforce_committee_lock "
    "directement via psycopg2."
)
def test_locked_committee_blocks_member_insert(db_conn, locked_committee):
    """
    INSERT dans committee_members pour un comité locked
    doit lever une exception PostgreSQL.
    🔴 BLOQUE CI quand actif.
    """
    pass


@pytest.mark.db_integrity
@pytest.mark.skip(reason="À implémenter dans M-COMMITTEE-CORE.")
def test_locked_committee_blocks_member_update(db_conn, locked_committee):
    """UPDATE dans committee_members doit être bloqué."""
    pass


@pytest.mark.db_integrity
@pytest.mark.skip(reason="À implémenter dans M-COMMITTEE-CORE.")
def test_locked_committee_blocks_member_delete(db_conn, locked_committee):
    """DELETE dans committee_members doit être bloqué."""
    pass


@pytest.mark.db_integrity
@pytest.mark.skip(reason="À implémenter dans M-COMMITTEE-CORE.")
def test_committee_lock_is_irreversible(db_conn, locked_committee):
    """
    UPDATE committees SET status='draft' sur un comité locked
    doit lever une exception (trigger prevent_committee_unlock).
    """
    pass
