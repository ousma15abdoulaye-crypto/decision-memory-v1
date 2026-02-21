"""Test extraction_corrections append-only semantics (INV-6, ADR-0006)."""

import json
import uuid

import psycopg
import pytest


@pytest.fixture
def setup_base_data(db_conn):
    cur = db_conn.cursor()
    case_id = f"corr-{uuid.uuid4().hex[:12]}"
    offer_id = f"offer-{uuid.uuid4().hex[:12]}"
    doc_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO users (email, username, hashed_password, full_name, is_active, is_superuser, role_id, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            f"test_{uuid.uuid4().hex[:8]}@test.com",
            f"testuser_{uuid.uuid4().hex[:8]}",
            "hash",
            "Test",
            True,
            False,
            1,
            "2026-02-21",
        ),
    )
    row = cur.fetchone()
    user_id = str(row["id"])
    cur.execute(
        "INSERT INTO cases (id, case_type, title, created_at, status) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (case_id, "CORR_TEST", "Fixture corrections", "2026-02-21", "active"),
    )
    cur.execute(
        "INSERT INTO offers (id, case_id, supplier_name, offer_type, submitted_at, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (offer_id, case_id, "Test", "technical", "2026-02-21", "2026-02-21"),
    )
    cur.execute(
        "INSERT INTO documents (id, case_id, offer_id, filename, path, uploaded_at) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (doc_id, case_id, offer_id, "test.pdf", "/tmp/test.pdf", "2026-02-21"),
    )
    db_conn.commit()
    return user_id, case_id, doc_id


def test_corrections_cannot_be_updated(db_conn, setup_base_data):
    cur = db_conn.cursor()
    user_id, case_id, doc_id = setup_base_data
    ext_id = str(uuid.uuid4())
    cor_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO extractions (id, case_id, document_id, structured_data, confidence_score, data_json, extraction_type, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (
            ext_id,
            case_id,
            doc_id,
            json.dumps({"test": "data"}),
            0.8,
            "{}",
            "native_pdf",
            "2026-02-21",
        ),
    )
    cur.execute(
        "INSERT INTO extraction_corrections (id, extraction_id, structured_data, corrected_by, correction_reason) VALUES (%s, %s, %s, %s, %s)",
        (cor_id, ext_id, json.dumps({"corrected": "v1"}), user_id, "initial fix"),
    )
    db_conn.commit()
    with pytest.raises(psycopg.Error) as exc_info:
        cur.execute(
            "UPDATE extraction_corrections SET structured_data = %s WHERE id = %s",
            (json.dumps({"corrected": "v2"}), cor_id),
        )
        db_conn.commit()
    assert "append-only" in str(exc_info.value).lower() or "INV-6" in str(
        exc_info.value
    )
    db_conn.rollback()


def test_corrections_cannot_be_deleted(db_conn, setup_base_data):
    cur = db_conn.cursor()
    user_id, case_id, doc_id = setup_base_data
    ext_id = str(uuid.uuid4())
    cor_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO extractions (id, case_id, document_id, structured_data, confidence_score, data_json, extraction_type, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (
            ext_id,
            case_id,
            doc_id,
            json.dumps({"test": "data"}),
            0.8,
            "{}",
            "native_pdf",
            "2026-02-21",
        ),
    )
    cur.execute(
        "INSERT INTO extraction_corrections (id, extraction_id, structured_data, corrected_by) VALUES (%s, %s, %s, %s)",
        (cor_id, ext_id, json.dumps({"corrected": "v1"}), user_id),
    )
    db_conn.commit()
    with pytest.raises(psycopg.Error) as exc_info:
        cur.execute("DELETE FROM extraction_corrections WHERE id = %s", (cor_id,))
        db_conn.commit()
    assert "append-only" in str(exc_info.value).lower() or "INV-6" in str(
        exc_info.value
    )
    db_conn.rollback()


def test_corrections_can_be_inserted(db_conn, setup_base_data):
    cur = db_conn.cursor()
    user_id, case_id, doc_id = setup_base_data
    ext_id = str(uuid.uuid4())
    cor_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO extractions (id, case_id, document_id, structured_data, confidence_score, data_json, extraction_type, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (
            ext_id,
            case_id,
            doc_id,
            json.dumps({"test": "data"}),
            0.8,
            "{}",
            "native_pdf",
            "2026-02-21",
        ),
    )
    cur.execute(
        "INSERT INTO extraction_corrections (id, extraction_id, structured_data, corrected_by, correction_reason) VALUES (%s, %s, %s, %s, %s)",
        (cor_id, ext_id, json.dumps({"corrected": "data"}), user_id, "fix typo"),
    )
    db_conn.commit()
    cur.execute("SELECT id FROM extraction_corrections WHERE id = %s", (cor_id,))
    result = cur.fetchone()
    assert result is not None
    assert result["id"] == cor_id


def test_effective_view_applies_corrections_in_order(db_conn, setup_base_data):
    cur = db_conn.cursor()
    user_id, case_id, doc_id = setup_base_data
    ext_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO extractions (id, case_id, document_id, structured_data, confidence_score, data_json, extraction_type, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (
            ext_id,
            case_id,
            doc_id,
            json.dumps({"original": "v0"}),
            0.5,
            "{}",
            "native_pdf",
            "2026-02-21",
        ),
    )
    cur.execute(
        "INSERT INTO extraction_corrections (id, extraction_id, structured_data, corrected_by) VALUES (%s, %s, %s, %s)",
        (str(uuid.uuid4()), ext_id, json.dumps({"v": "1"}), user_id),
    )
    cur.execute(
        "INSERT INTO extraction_corrections (id, extraction_id, structured_data, corrected_by) VALUES (%s, %s, %s, %s)",
        (str(uuid.uuid4()), ext_id, json.dumps({"v": "2"}), user_id),
    )
    db_conn.commit()
    cur.execute(
        "SELECT structured_data FROM structured_data_effective WHERE extraction_id = %s",
        (ext_id,),
    )
    result = cur.fetchone()
    assert result is not None
    data = result["structured_data"]
    if isinstance(data, str):
        data = json.loads(data)
    assert data.get("v") == "2", f"Expected latest correction (v=2), got {data}"
