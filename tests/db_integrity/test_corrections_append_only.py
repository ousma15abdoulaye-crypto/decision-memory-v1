"""Test extraction_corrections append-only semantics (INV-6, ADR-0006)."""

import uuid
import json
import pytest
import psycopg


@pytest.fixture
def setup_base_data(db_conn):
    """Create users → cases → documents → extractions (fixtures)."""
    cur = db_conn.cursor()
    
    user_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    
    # Insert user
    cur.execute(
        "INSERT INTO users (id, email, password_hash, role) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (user_id, "test@test.com", "hash", "admin")
    )
    
    # Insert case
    cur.execute(
        "INSERT INTO cases (id, code, owner_user_id, status) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (case_id, f"TEST-{uuid.uuid4().hex[:4]}", user_id, "active")
    )
    
    # Insert document
    cur.execute(
        "INSERT INTO documents (id, case_id, filename, mimetype, file_size) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (doc_id, case_id, "test.pdf", "application/pdf", 1024)
    )
    
    db_conn.commit()
    return user_id, case_id, doc_id


def test_corrections_cannot_be_updated(db_conn, setup_base_data):
    """INVARIANT INV-6: extraction_corrections is append-only → UPDATE forbidden."""
    cur = db_conn.cursor()
    user_id, case_id, doc_id = setup_base_data
    
    ext_id = str(uuid.uuid4())
    cor_id = str(uuid.uuid4())
    
    # Insert extraction
    cur.execute(
        "INSERT INTO extractions (id, document_id, structured_data, confidence_score) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (ext_id, doc_id, json.dumps({"test": "data"}), 0.8)
    )
    
    # Insert correction
    cur.execute(
        "INSERT INTO extraction_corrections "
        "(id, extraction_id, structured_data, corrected_by, correction_reason) "
        "VALUES (%s, %s, %s, %s, %s)",
        (cor_id, ext_id, json.dumps({"corrected": "v1"}), user_id, "initial fix")
    )
    db_conn.commit()
    
    # Try UPDATE → must raise EXCEPTION
    with pytest.raises(psycopg.Error) as exc_info:
        cur.execute(
            "UPDATE extraction_corrections SET structured_data = %s WHERE id = %s",
            (json.dumps({"corrected": "v2"}), cor_id)
        )
        db_conn.commit()
    
    assert "append-only" in str(exc_info.value).lower() or "INV-6" in str(exc_info.value)
    db_conn.rollback()


def test_corrections_cannot_be_deleted(db_conn, setup_base_data):
    """INVARIANT INV-6: extraction_corrections is append-only → DELETE forbidden."""
    cur = db_conn.cursor()
    user_id, case_id, doc_id = setup_base_data
    
    ext_id = str(uuid.uuid4())
    cor_id = str(uuid.uuid4())
    
    # Insert extraction + correction
    cur.execute(
        "INSERT INTO extractions (id, document_id, structured_data, confidence_score) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (ext_id, doc_id, json.dumps({"test": "data"}), 0.8)
    )
    cur.execute(
        "INSERT INTO extraction_corrections "
        "(id, extraction_id, structured_data, corrected_by) "
        "VALUES (%s, %s, %s, %s)",
        (cor_id, ext_id, json.dumps({"corrected": "v1"}), user_id)
    )
    db_conn.commit()
    
    # Try DELETE → must raise EXCEPTION
    with pytest.raises(psycopg.Error) as exc_info:
        cur.execute("DELETE FROM extraction_corrections WHERE id = %s", (cor_id,))
        db_conn.commit()
    
    assert "append-only" in str(exc_info.value).lower() or "INV-6" in str(exc_info.value)
    db_conn.rollback()


def test_corrections_can_be_inserted(db_conn, setup_base_data):
    """INSERT into extraction_corrections must succeed (append operation)."""
    cur = db_conn.cursor()
    user_id, case_id, doc_id = setup_base_data
    
    ext_id = str(uuid.uuid4())
    cor_id = str(uuid.uuid4())
    
    # Insert extraction
    cur.execute(
        "INSERT INTO extractions (id, document_id, structured_data, confidence_score) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (ext_id, doc_id, json.dumps({"test": "data"}), 0.8)
    )
    
    # Insert correction
    cur.execute(
        "INSERT INTO extraction_corrections "
        "(id, extraction_id, structured_data, corrected_by, correction_reason) "
        "VALUES (%s, %s, %s, %s, %s)",
        (cor_id, ext_id, json.dumps({"corrected": "data"}), user_id, "fix typo")
    )
    db_conn.commit()
    
    # Verify inserted
    cur.execute("SELECT id FROM extraction_corrections WHERE id = %s", (cor_id,))
    result = cur.fetchone()
    assert result is not None
    assert result[0] == cor_id


def test_effective_view_applies_corrections_in_order(db_conn, setup_base_data):
    """ADR-0006: View structured_data_effective shows latest correction."""
    cur = db_conn.cursor()
    user_id, case_id, doc_id = setup_base_data
    
    ext_id = str(uuid.uuid4())
    
    # Insert extraction with original data
    cur.execute(
        "INSERT INTO extractions (id, document_id, structured_data, confidence_score) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (ext_id, doc_id, json.dumps({"original": "v0"}), 0.5)
    )
    
    # Correction 1
    cur.execute(
        "INSERT INTO extraction_corrections "
        "(id, extraction_id, structured_data, corrected_by) "
        "VALUES (%s, %s, %s, %s)",
        (str(uuid.uuid4()), ext_id, json.dumps({"v": "1"}), user_id)
    )
    
    # Correction 2 (latest — view should show this)
    cur.execute(
        "INSERT INTO extraction_corrections "
        "(id, extraction_id, structured_data, corrected_by) "
        "VALUES (%s, %s, %s, %s)",
        (str(uuid.uuid4()), ext_id, json.dumps({"v": "2"}), user_id)
    )
    db_conn.commit()
    
    # View should return LATEST correction (v=2)
    cur.execute(
        "SELECT structured_data FROM structured_data_effective WHERE extraction_id = %s",
        (ext_id,)
    )
    result = cur.fetchone()
    assert result is not None
    
    # Handle both JSON string and dict
    data = result[0]
    if isinstance(data, str):
        data = json.loads(data)
    
    assert data.get("v") == "2", f"Expected latest correction (v=2), got {data}"
