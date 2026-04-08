"""INV-S03 — deliberation_messages append-only (Canon V5.1.0 Locking test 7).

`deliberation_messages` et `pv_snapshot` sont append-only via trigger DB.
Ce fichier couvre la partie `deliberation_messages`.
Nécessite une DB de test connectée (mark db_integrity).
"""

from __future__ import annotations

import pytest


@pytest.mark.db_integrity
def test_update_message_body_blocked(db_conn) -> None:
    """INV-S03 : UPDATE sur deliberation_messages.body est bloqué."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id::text FROM deliberation_messages LIMIT 1")
        row = cur.fetchone()
    if not row:
        pytest.skip("aucun deliberation_messages en base de test")

    mid = row["id"]
    with pytest.raises(Exception):
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE deliberation_messages SET body = %s WHERE id = %s::uuid",
                ("tampered", mid),
            )


@pytest.mark.db_integrity
def test_delete_message_blocked(db_conn) -> None:
    """INV-S03 : DELETE sur deliberation_messages est bloqué."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id::text FROM deliberation_messages LIMIT 1")
        row = cur.fetchone()
    if not row:
        pytest.skip("aucun deliberation_messages en base de test")

    mid = row["id"]
    with pytest.raises(Exception):
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM deliberation_messages WHERE id = %s::uuid", (mid,))


@pytest.mark.db_integrity
def test_update_author_blocked(db_conn) -> None:
    """INV-S03 : UPDATE sur author_user_id est aussi bloqué (mutation complète)."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id::text FROM deliberation_messages LIMIT 1")
        row = cur.fetchone()
    if not row:
        pytest.skip("aucun deliberation_messages en base de test")

    mid = row["id"]
    with pytest.raises(Exception):
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE deliberation_messages SET author_user_id = 9999 WHERE id = %s::uuid",
                (mid,),
            )
