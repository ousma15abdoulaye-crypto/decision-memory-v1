"""
Test : Append-only corrections humaines
Gate : BLOQUANT CI (M-EXTRACTION-CORRECTIONS)
ADR  : ADR-0002 §6.2, ADR-0007
INV  : INV-6 (append-only) + INV-9 (fidélité au réel)

Consolidé : ex-invariants/phase0/test_corrections_append_only.py
"""

import json

import pytest


@pytest.mark.db_integrity
def test_corrections_cannot_be_updated(db_conn, extraction_correction_fixture):
    """
    Un UPDATE sur extraction_corrections doit lever une exception.
    Trigger : enforce_extraction_corrections_append_only
    """
    _doc_id, _ext_id, correction_id = extraction_correction_fixture
    with db_conn.cursor() as cur:
        with pytest.raises(Exception) as exc_info:
            cur.execute(
                "UPDATE extraction_corrections SET correction_reason = 'x' WHERE id = %s",
                (correction_id,),
            )
        msg = str(exc_info.value).lower()
        assert "append-only" in msg or "inv-6" in msg or "violation" in msg


@pytest.mark.db_integrity
def test_corrections_cannot_be_deleted(db_conn, extraction_correction_fixture):
    """Un DELETE sur extraction_corrections doit lever une exception."""
    _doc_id, _ext_id, correction_id = extraction_correction_fixture
    with db_conn.cursor() as cur:
        with pytest.raises(Exception) as exc_info:
            cur.execute(
                "DELETE FROM extraction_corrections WHERE id = %s", (correction_id,)
            )
        msg = str(exc_info.value).lower()
        assert "append-only" in msg or "inv-6" in msg or "violation" in msg


@pytest.mark.db_integrity
def test_corrections_can_be_inserted(db_conn, extraction_correction_fixture):
    """Un INSERT valide doit réussir (append autorisé)."""
    doc_id, extraction_id, _ = extraction_correction_fixture
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO extraction_corrections
                (extraction_id, structured_data,
                 confidence_override, correction_reason, corrected_by)
            VALUES (%s, '{"new": true}'::jsonb, 0.99, 'insert test', 'test-user')
            RETURNING id
            """,
            (extraction_id,),
        )
        row = cur.fetchone()
    assert row is not None and row.get("id") is not None


@pytest.mark.db_integrity
def test_effective_view_applies_corrections_in_order(
    db_conn, extraction_correction_fixture
):
    """
    La vue structured_data_effective retourne la correction
    (dernière correction appliquée) et non l'original.
    """
    doc_id, _extraction_id, _ = extraction_correction_fixture
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT structured_data, confidence_score
            FROM structured_data_effective
            WHERE document_id = %s
            """,
            (doc_id,),
        )
        row = cur.fetchone()
    assert row is not None
    sd = row.get("structured_data")
    if isinstance(sd, str):
        sd = json.loads(sd)
    assert sd is not None
    assert sd.get("corrected") is True or row.get("confidence_score") >= 0.95
