"""INV-D02 — CHECK constraints score/confidence (Canon V5.1.0 Locking test 9).

score dans [0, 1000]. confidence dans [0, 1].
Ces contraintes sont imposées via CHECK sur les tables DB.
Nécessite une DB de test connectée (mark db_integrity).
"""

from __future__ import annotations

import uuid

import pytest


@pytest.mark.db_integrity
def test_criterion_assessment_confidence_out_of_range_rejected(db_conn) -> None:
    """INV-D02 : confidence > 1.0 dans criterion_assessments est rejeté."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT cs.workspace_id::text, cs.tenant_id::text
            FROM committee_sessions cs
            LIMIT 1
            """)
        row = cur.fetchone()
    if not row:
        pytest.skip("aucune committee_session en base de test")

    bad_id = str(uuid.uuid4())
    with pytest.raises(Exception):
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO criterion_assessments
                    (id, workspace_id, tenant_id, bundle_id, criterion_key, confidence, assessment_status)
                VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, 'k1', 1.5, 'draft')
                """,
                (bad_id, row["workspace_id"], row["tenant_id"], str(uuid.uuid4())),
            )


@pytest.mark.db_integrity
def test_criterion_assessment_negative_confidence_rejected(db_conn) -> None:
    """INV-D02 : confidence < 0 dans criterion_assessments est rejeté."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT cs.workspace_id::text, cs.tenant_id::text
            FROM committee_sessions cs
            LIMIT 1
            """)
        row = cur.fetchone()
    if not row:
        pytest.skip("aucune committee_session en base de test")

    bad_id = str(uuid.uuid4())
    with pytest.raises(Exception):
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO criterion_assessments
                    (id, workspace_id, tenant_id, bundle_id, criterion_key, confidence, assessment_status)
                VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, 'k1', -0.1, 'draft')
                """,
                (bad_id, row["workspace_id"], row["tenant_id"], str(uuid.uuid4())),
            )
