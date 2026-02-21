"""Test database-level triggers for extraction_corrections append-only."""

import json
import uuid

import psycopg
import pytest


@pytest.fixture
def setup_trigger_test_data(db_conn):
    cur = db_conn.cursor()
    case_id = f"trig-{uuid.uuid4().hex[:12]}"
    offer_id = f"offer-{uuid.uuid4().hex[:12]}"
    doc_id = str(uuid.uuid4())
    ext_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO users (email, username, hashed_password, full_name, is_active, is_superuser, role_id, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            f"trigger_{uuid.uuid4().hex[:8]}@test.com",
            f"triguser_{uuid.uuid4().hex[:8]}",
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
        (case_id, "TRIG_TEST", "Fixture triggers", "2026-02-21", "active"),
    )
    cur.execute(
        "INSERT INTO offers (id, case_id, supplier_name, offer_type, submitted_at, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (offer_id, case_id, "Test", "technical", "2026-02-21", "2026-02-21"),
    )
    cur.execute(
        "INSERT INTO documents (id, case_id, offer_id, filename, path, uploaded_at) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (
            doc_id,
            case_id,
            offer_id,
            "trigger_test.pdf",
            "/tmp/trigger.pdf",
            "2026-02-21",
        ),
    )
    cur.execute(
        "INSERT INTO extractions (id, case_id, document_id, structured_data, confidence_score, data_json, extraction_type, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (
            ext_id,
            case_id,
            doc_id,
            json.dumps({"trigger": "test"}),
            0.7,
            "{}",
            "native_pdf",
            "2026-02-21",
        ),
    )
    db_conn.commit()
    return user_id, ext_id


def test_trigger_enforce_corrections_append_only_blocks_update(
    db_conn, setup_trigger_test_data
):
    cur = db_conn.cursor()
    user_id, ext_id = setup_trigger_test_data
    cor_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO extraction_corrections (id, extraction_id, structured_data, corrected_by) VALUES (%s, %s, %s, %s)",
        (cor_id, ext_id, json.dumps({"status": "draft"}), user_id),
    )
    db_conn.commit()
    with pytest.raises(psycopg.Error) as exc_info:
        cur.execute(
            "UPDATE extraction_corrections SET structured_data = %s WHERE id = %s",
            (json.dumps({"status": "published"}), cor_id),
        )
        db_conn.commit()
    error_msg = str(exc_info.value).lower()
    assert "append-only" in error_msg or "inv-6" in error_msg
    db_conn.rollback()


def test_trigger_enforce_corrections_append_only_blocks_delete(
    db_conn, setup_trigger_test_data
):
    cur = db_conn.cursor()
    user_id, ext_id = setup_trigger_test_data
    cor_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO extraction_corrections (id, extraction_id, structured_data, corrected_by) VALUES (%s, %s, %s, %s)",
        (cor_id, ext_id, json.dumps({"status": "draft"}), user_id),
    )
    db_conn.commit()
    with pytest.raises(psycopg.Error) as exc_info:
        cur.execute("DELETE FROM extraction_corrections WHERE id = %s", (cor_id,))
        db_conn.commit()
    error_msg = str(exc_info.value).lower()
    assert "append-only" in error_msg or "inv-6" in error_msg
    db_conn.rollback()
