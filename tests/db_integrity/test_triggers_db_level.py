"""
Tests : Triggers PostgreSQL — intégrité DB niveau bas
Gate  : BLOQUANT CI (M-EXTRACTION-CORRECTIONS)
ADR   : ADR-0002 §2.6, ADR-0007
INV   : INV-6
"""

import pytest


@pytest.mark.db_integrity
def test_trigger_enforce_corrections_append_only_blocks_update(
    db_conn, extraction_correction_fixture
):
    """
    UPDATE direct sur extraction_corrections doit lever une exception.
    Trigger : enforce_extraction_corrections_append_only
    """
    _doc_id, _ext_id, correction_id = extraction_correction_fixture
    with db_conn.cursor() as cur:
        with pytest.raises(Exception) as exc_info:
            cur.execute(
                """
                UPDATE extraction_corrections
                SET correction_reason = 'hacked'
                WHERE id = %s
                """,
                (correction_id,),
            )
        msg = str(exc_info.value).lower()
        assert "append-only" in msg or "inv-6" in msg or "violation" in msg


@pytest.mark.db_integrity
def test_trigger_enforce_corrections_append_only_blocks_delete(
    db_conn, extraction_correction_fixture
):
    """DELETE direct sur extraction_corrections doit lever une exception."""
    _doc_id, _ext_id, correction_id = extraction_correction_fixture
    with db_conn.cursor() as cur:
        with pytest.raises(Exception) as exc_info:
            cur.execute(
                "DELETE FROM extraction_corrections WHERE id = %s",
                (correction_id,),
            )
        msg = str(exc_info.value).lower()
        assert "append-only" in msg or "inv-6" in msg or "violation" in msg
