"""INV-W05 — pv_snapshot figé après seal (Canon V5.1.0 Locking test 2).

Trigger PostgreSQL immutabilité sur committee_sessions après seal.
INV-W02 : scellement irréversible. INV-W05 : trigger immutabilité.
Nécessite une DB de test connectée (mark db_integrity).
"""

from __future__ import annotations

import pytest


@pytest.mark.db_integrity
def test_sealed_session_pv_snapshot_cannot_be_updated(db_conn) -> None:
    """INV-W05 : UPDATE pv_snapshot sur session scellée est bloqué."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT id::text
            FROM committee_sessions
            WHERE session_status = 'sealed'
            LIMIT 1
            """)
        row = cur.fetchone()
    if not row:
        pytest.skip("aucune session scellée en base de test")

    session_id = row["id"]
    with pytest.raises(Exception):
        with db_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE committee_sessions
                SET pv_snapshot = '{"tampered": true}'::jsonb
                WHERE id = %s::uuid
                  AND session_status = 'sealed'
                """,
                (session_id,),
            )


@pytest.mark.db_integrity
def test_sealed_session_seal_hash_cannot_be_changed(db_conn) -> None:
    """INV-W05 : UPDATE seal_hash sur session scellée est bloqué."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT id::text
            FROM committee_sessions
            WHERE session_status = 'sealed'
              AND seal_hash IS NOT NULL
            LIMIT 1
            """)
        row = cur.fetchone()
    if not row:
        pytest.skip("aucune session scellée avec seal_hash en base de test")

    session_id = row["id"]
    with pytest.raises(Exception):
        with db_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE committee_sessions
                SET seal_hash = 'fake-hash-tampered'
                WHERE id = %s::uuid
                  AND session_status = 'sealed'
                """,
                (session_id,),
            )


@pytest.mark.db_integrity
def test_sealed_status_cannot_be_reverted(db_conn) -> None:
    """INV-W02 : scellement irréversible — session_status ne peut pas repasser à 'open'."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT id::text
            FROM committee_sessions
            WHERE session_status = 'sealed'
            LIMIT 1
            """)
        row = cur.fetchone()
    if not row:
        pytest.skip("aucune session scellée en base de test")

    session_id = row["id"]
    with pytest.raises(Exception):
        with db_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE committee_sessions
                SET session_status = 'open'
                WHERE id = %s::uuid
                """,
                (session_id,),
            )
