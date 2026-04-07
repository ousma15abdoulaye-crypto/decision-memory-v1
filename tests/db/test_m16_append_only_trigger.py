"""F10 — trigger append-only sur deliberation_messages."""

from __future__ import annotations

import pytest


@pytest.mark.db_integrity
def test_update_message_blocked(db_conn) -> None:
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT id::text FROM deliberation_messages
            LIMIT 1
            """)
        row = cur.fetchone()
    if not row:
        pytest.skip("aucun deliberation_messages en base de test")

    mid = row["id"]
    with pytest.raises(Exception):
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE deliberation_messages SET body = %s WHERE id = %s::uuid",
                ("x", mid),
            )


@pytest.mark.db_integrity
def test_delete_message_blocked(db_conn) -> None:
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT id::text FROM deliberation_messages
            LIMIT 1
            """)
        row = cur.fetchone()
    if not row:
        pytest.skip("aucun deliberation_messages en base de test")

    mid = row["id"]
    with pytest.raises(Exception):
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM deliberation_messages WHERE id = %s::uuid",
                (mid,),
            )
