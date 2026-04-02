"""
Tests M12 Correction Writer — src/procurement/m12_correction_writer.py

Règles : zéro API réelle, zéro réseau, mocks connexion uniquement.
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

import pytest

from src.procurement.m12_correction_writer import (
    M12CorrectionEntry,
    M12CorrectionWriter,
)


class MockConn:
    """Connexion minimale : dernier SQL + params pour assertions."""

    def __init__(self):
        self.last_sql: str | None = None
        self.last_params: dict | None = None
        self._next_fetchone: dict | None = None
        self._next_fetchall: list[dict] = []

    def execute(self, sql: str, params: dict | None = None) -> None:
        self.last_sql = sql.strip()
        self.last_params = params or {}

    def fetchone(self) -> dict | None:
        return self._next_fetchone

    def fetchall(self) -> list[dict]:
        return self._next_fetchall

    def set_fetchone(self, row: dict | None) -> None:
        self._next_fetchone = row

    def set_fetchall(self, rows: list[dict]) -> None:
        self._next_fetchall = rows


@pytest.fixture
def writer() -> M12CorrectionWriter:
    return M12CorrectionWriter()


@pytest.fixture
def sample_run_id() -> UUID:
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def valid_entry(sample_run_id: UUID) -> M12CorrectionEntry:
    return M12CorrectionEntry(
        document_id="doc_001",
        run_id=sample_run_id,
        correction_type="document_kind",
        field_corrected="procedure_recognition.document_kind",
        original_value={"text": "offer_technical"},
        corrected_value={"text": "evaluation_doc"},
        corrected_by="human",
        pass_origin="1A",
        confidence_was=0.72,
        corpus_size_at_correction=87,
    )


class TestM12CorrectionEntry:
    def test_valid_minimal(self, sample_run_id: UUID):
        e = M12CorrectionEntry(
            document_id="d1",
            run_id=sample_run_id,
            correction_type="other",
            field_corrected="x",
            corrected_by="human",
        )
        assert e.original_value == {}
        assert e.correction_note is None

    def test_valid_full(self, valid_entry: M12CorrectionEntry):
        assert valid_entry.document_id == "doc_001"
        assert valid_entry.confidence_was == 0.72

    def test_rejects_empty_document_id(self, sample_run_id: UUID):
        with pytest.raises(ValueError):
            M12CorrectionEntry(
                document_id="",
                run_id=sample_run_id,
                correction_type="other",
                field_corrected="f",
                corrected_by="human",
            )

    def test_rejects_empty_field_corrected(self, sample_run_id: UUID):
        with pytest.raises(ValueError):
            M12CorrectionEntry(
                document_id="d",
                run_id=sample_run_id,
                correction_type="other",
                field_corrected="",
                corrected_by="human",
            )

    def test_rejects_bad_correction_type(self, sample_run_id: UUID):
        with pytest.raises(ValueError):
            M12CorrectionEntry(
                document_id="d",
                run_id=sample_run_id,
                correction_type="invalid_type",
                field_corrected="f",
                corrected_by="human",
            )

    def test_rejects_confidence_above_1(self, sample_run_id: UUID):
        with pytest.raises(ValueError):
            M12CorrectionEntry(
                document_id="d",
                run_id=sample_run_id,
                correction_type="other",
                field_corrected="f",
                corrected_by="human",
                confidence_was=1.5,
            )

    def test_rejects_negative_corpus(self, sample_run_id: UUID):
        with pytest.raises(ValueError):
            M12CorrectionEntry(
                document_id="d",
                run_id=sample_run_id,
                correction_type="other",
                field_corrected="f",
                corrected_by="human",
                corpus_size_at_correction=-1,
            )

    def test_confidence_boundaries(self, sample_run_id: UUID):
        e0 = M12CorrectionEntry(
            document_id="d",
            run_id=sample_run_id,
            correction_type="other",
            field_corrected="f",
            corrected_by="human",
            confidence_was=0.0,
        )
        assert e0.confidence_was == 0.0
        e1 = M12CorrectionEntry(
            document_id="d",
            run_id=sample_run_id,
            correction_type="other",
            field_corrected="f",
            corrected_by="human",
            confidence_was=1.0,
        )
        assert e1.confidence_was == 1.0

    def test_resolved_correction_note_json(self, valid_entry: M12CorrectionEntry):
        note = valid_entry.resolved_correction_note()
        assert note is not None
        meta = json.loads(note)
        assert meta["pass_origin"] == "1A"
        assert meta["confidence_was"] == 0.72
        assert meta["corpus_size_at_correction"] == 87

    def test_extra_forbidden(self, sample_run_id: UUID):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            M12CorrectionEntry(
                document_id="d",
                run_id=sample_run_id,
                correction_type="other",
                field_corrected="f",
                corrected_by="human",
                typo_field=1,  # type: ignore[call-arg]
            )


class TestM12CorrectionWriter:
    def test_write_returns_id(
        self, writer: M12CorrectionWriter, valid_entry: M12CorrectionEntry
    ):
        conn = MockConn()
        conn.set_fetchone({"id": 42})
        rid = writer.write(conn, valid_entry)
        assert rid == 42
        assert conn.last_params is not None
        assert conn.last_params["document_id"] == "doc_001"
        assert conn.last_params["correction_type"] == "document_kind"
        assert conn.last_params["field_corrected"] == (
            "procedure_recognition.document_kind"
        )
        assert json.loads(conn.last_params["original_value"]) == {
            "text": "offer_technical"
        }
        assert json.loads(conn.last_params["corrected_value"]) == {
            "text": "evaluation_doc"
        }
        assert conn.last_params["corrected_by"] == "human"
        assert conn.last_params["run_id"] == str(valid_entry.run_id)
        assert conn.last_params["correction_note"] is not None

    def test_write_batch(self, writer: M12CorrectionWriter, sample_run_id: UUID):
        conn = MockConn()
        seq = iter([1, 2, 3])

        def exec_wrap(sql: str, params: dict | None = None) -> None:
            conn.last_sql = sql.strip()
            conn.last_params = params or {}
            conn.set_fetchone({"id": next(seq)})

        conn.execute = exec_wrap  # type: ignore[method-assign]

        entries = [
            M12CorrectionEntry(
                document_id=f"doc_{i}",
                run_id=sample_run_id,
                correction_type="other",
                field_corrected="f",
                corrected_by="human",
            )
            for i in range(3)
        ]
        ids = writer.write_batch(conn, entries)
        assert ids == [1, 2, 3]

    def test_write_batch_empty(self, writer: M12CorrectionWriter):
        conn = MockConn()
        assert writer.write_batch(conn, []) == []

    def test_count_total(self, writer: M12CorrectionWriter):
        conn = MockConn()
        conn.set_fetchone({"c": 42})
        assert writer.count_total(conn) == 42

    def test_count_by_field(self, writer: M12CorrectionWriter):
        conn = MockConn()
        conn.set_fetchone({"c": 7})
        n = writer.count_by_field(conn, "procedure_recognition.document_kind")
        assert n == 7
        assert conn.last_params == {
            "field_corrected": "procedure_recognition.document_kind"
        }

    def test_count_by_document(self, writer: M12CorrectionWriter):
        conn = MockConn()
        conn.set_fetchone({"c": 3})
        assert writer.count_by_document(conn, "doc_001") == 3

    def test_get_recent(self, writer: M12CorrectionWriter):
        conn = MockConn()
        now = datetime.utcnow()
        conn.set_fetchall(
            [
                {
                    "id": 1,
                    "document_id": "doc_001",
                    "field_corrected": "a",
                    "created_at": now,
                },
                {
                    "id": 2,
                    "document_id": "doc_002",
                    "field_corrected": "b",
                    "created_at": now,
                },
            ]
        )
        rows = writer.get_recent(conn, limit=5)
        assert len(rows) == 2
        assert rows[0]["id"] == 1

    def test_get_recent_empty(self, writer: M12CorrectionWriter):
        conn = MockConn()
        conn.set_fetchall([])
        assert writer.get_recent(conn) == []

    def test_get_recent_rejects_limit_below_one(self, writer: M12CorrectionWriter):
        conn = MockConn()
        with pytest.raises(ValueError, match="limit must be >= 1"):
            writer.get_recent(conn, limit=0)

    def test_get_recent_caps_limit(self, writer: M12CorrectionWriter):
        conn = MockConn()
        conn.set_fetchall([])
        writer.get_recent(conn, limit=5000)
        assert conn.last_params == {"limit": 1000}

    def test_rate_last_30d_with_data(self, writer: M12CorrectionWriter):
        conn = MockConn()
        conn.set_fetchone({"corrections": 15, "documents_corrected": 10})
        assert writer.rate_last_30d(conn) == 1.5

    def test_rate_last_30d_no_data(self, writer: M12CorrectionWriter):
        conn = MockConn()
        conn.set_fetchone({"corrections": 0, "documents_corrected": 0})
        assert writer.rate_last_30d(conn) == 0.0

    def test_rate_last_30d_zero_documents(self, writer: M12CorrectionWriter):
        conn = MockConn()
        conn.set_fetchone({"corrections": 5, "documents_corrected": 0})
        assert writer.rate_last_30d(conn) == 0.0


class TestM12CorrectionWriterGuardRails:
    def test_no_update_delete_methods(self, writer: M12CorrectionWriter):
        assert not hasattr(writer, "update")
        assert not hasattr(writer, "delete")
        assert not hasattr(writer, "edit")
        assert not hasattr(writer, "modify")
        assert not hasattr(writer, "remove")
        assert not hasattr(writer, "purge")

    def test_insert_sql_safe(self, writer: M12CorrectionWriter):
        sql = writer._INSERT_SQL.upper()
        assert "UPDATE" not in sql
        assert "DELETE" not in sql

    def test_all_sql_strings_safe(self, writer: M12CorrectionWriter):
        for name in dir(writer):
            if name.endswith("_SQL"):
                sql = str(getattr(writer, name)).upper()
                assert "UPDATE" not in sql
                assert "DELETE" not in sql
                assert "DROP" not in sql
                assert "TRUNCATE" not in sql
                assert "ALTER" not in sql
