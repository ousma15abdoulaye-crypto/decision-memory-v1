"""INV-S04 — assessment_comments content/is_flag immutables (Locking test 8).

Canon V5.1.0 INV-S04 — trigger `trg_ac_content_immutable`.
`content` et `is_flag` sont immutables après insertion.
`resolved` peut être modifié (pour résoudre un flag).
Nécessite une DB de test connectée (mark db_integrity).
"""

from __future__ import annotations

import pytest


@pytest.mark.db_integrity
def test_update_content_blocked(db_conn) -> None:
    """INV-S04 : UPDATE content sur assessment_comments est bloqué."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id::text FROM assessment_comments LIMIT 1")
        row = cur.fetchone()
    if not row:
        pytest.skip("aucun assessment_comments en base de test")

    cid = row["id"]
    with pytest.raises(Exception, match="immutables|immutable|INV-S04"):
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE assessment_comments SET content = %s WHERE id = %s::uuid",
                ("tampered content", cid),
            )


@pytest.mark.db_integrity
def test_update_is_flag_blocked(db_conn) -> None:
    """INV-S04 : UPDATE is_flag sur assessment_comments est bloqué."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id::text, is_flag FROM assessment_comments LIMIT 1")
        row = cur.fetchone()
    if not row:
        pytest.skip("aucun assessment_comments en base de test")

    cid = row["id"]
    new_flag = not row["is_flag"]
    with pytest.raises(Exception, match="immutables|immutable|INV-S04"):
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE assessment_comments SET is_flag = %s WHERE id = %s::uuid",
                (new_flag, cid),
            )


@pytest.mark.db_integrity
def test_update_resolved_allowed(db_conn) -> None:
    """INV-S04 : UPDATE resolved est autorisé (seul champ mutable)."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT id::text FROM assessment_comments WHERE resolved = FALSE LIMIT 1"
        )
        row = cur.fetchone()
    if not row:
        pytest.skip("aucun assessment_comments non résolu en base de test")

    cid = row["id"]
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE assessment_comments SET resolved = TRUE, resolved_at = NOW() WHERE id = %s::uuid",
            (cid,),
        )
