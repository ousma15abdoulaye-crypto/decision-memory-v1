"""Tests — M13CorrectionEntry + M13CorrectionWriter (pattern M12)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from src.procurement.m13_correction_writer import (
    _MAX_RECENT_LIMIT,
    M13CorrectionEntry,
    M13CorrectionWriter,
)

# ── Mock connexion ──────────────────────────────────────────────


class MockConn:
    def __init__(self) -> None:
        self.last_sql: str = ""
        self.last_params: dict[str, Any] | None = None
        self._fetchone_result: dict[str, Any] | None = None
        self._fetchall_result: list[dict[str, Any]] = []

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        self.last_sql = sql
        self.last_params = params

    def fetchone(self) -> dict[str, Any] | None:
        return self._fetchone_result

    def fetchall(self) -> list[dict[str, Any]]:
        return self._fetchall_result

    def set_fetchone(self, result: dict[str, Any] | None) -> None:
        self._fetchone_result = result

    def set_fetchall(self, result: list[dict[str, Any]]) -> None:
        self._fetchall_result = result


def _valid_entry(**overrides: Any) -> M13CorrectionEntry:
    defaults: dict[str, Any] = {
        "case_id": "CASE-001",
        "field_path": "regime.procedure_type",
        "value_predicted": "open_national",
        "value_corrected": "restricted",
        "layer_origin": "regime_resolver",
        "confidence_was": 0.8,
        "correction_source": "human_annotator",
        "corpus_size_at_correction": 42,
    }
    defaults.update(overrides)
    return M13CorrectionEntry(**defaults)


# ── TestM13CorrectionEntry ──────────────────────────────────────


class TestM13CorrectionEntry:
    def test_valid_entry(self) -> None:
        entry = _valid_entry()
        assert entry.case_id == "CASE-001"
        assert entry.field_path == "regime.procedure_type"

    def test_empty_case_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _valid_entry(case_id="")

    def test_empty_field_path_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _valid_entry(field_path="")

    def test_confidence_bounds_low(self) -> None:
        with pytest.raises(ValidationError):
            _valid_entry(confidence_was=-0.1)

    def test_confidence_bounds_high(self) -> None:
        with pytest.raises(ValidationError):
            _valid_entry(confidence_was=1.1)

    def test_corpus_size_negative(self) -> None:
        with pytest.raises(ValidationError):
            _valid_entry(corpus_size_at_correction=-1)

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            _valid_entry(rogue_field="hacked")

    def test_nullable_fields_accept_none(self) -> None:
        entry = _valid_entry(
            value_predicted=None,
            value_corrected=None,
            layer_origin=None,
            confidence_was=None,
            correction_source=None,
            corpus_size_at_correction=None,
        )
        assert entry.value_predicted is None
        assert entry.value_corrected is None

    def test_resolved_metadata_json_full(self) -> None:
        entry = _valid_entry()
        meta = entry.resolved_metadata_json()
        assert meta is not None
        import json

        parsed = json.loads(meta)
        assert parsed["layer_origin"] == "regime_resolver"
        assert parsed["confidence_was"] == 0.8
        assert parsed["corpus_size_at_correction"] == 42

    def test_resolved_metadata_json_none_when_empty(self) -> None:
        entry = _valid_entry(
            layer_origin=None,
            confidence_was=None,
            corpus_size_at_correction=None,
        )
        assert entry.resolved_metadata_json() is None


# ── TestM13CorrectionWriter ─────────────────────────────────────


class TestM13CorrectionWriter:
    def test_write_returns_id(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"id": 7})
        writer = M13CorrectionWriter()
        rid = writer.write(conn, _valid_entry())
        assert rid == 7
        assert "INSERT INTO m13_correction_log" in conn.last_sql
        assert conn.last_params is not None
        assert conn.last_params["case_id"] == "CASE-001"

    def test_write_params_complete(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"id": 1})
        writer = M13CorrectionWriter()
        writer.write(conn, _valid_entry())
        p = conn.last_params
        assert p is not None
        expected_keys = {
            "case_id",
            "field_path",
            "value_predicted",
            "value_corrected",
            "layer_origin",
            "confidence_was",
            "correction_source",
            "corpus_size_at_correction",
        }
        assert set(p.keys()) == expected_keys

    def test_write_raises_on_no_returning(self) -> None:
        conn = MockConn()
        conn.set_fetchone(None)
        writer = M13CorrectionWriter()
        with pytest.raises(RuntimeError, match="RETURNING id"):
            writer.write(conn, _valid_entry())

    def test_write_batch(self) -> None:
        conn = MockConn()
        _id_counter = iter(range(1, 100))

        original_execute = conn.execute

        def _tracking_execute(sql: str, params: dict[str, Any] | None = None) -> None:
            original_execute(sql, params)
            conn.set_fetchone({"id": next(_id_counter)})

        conn.execute = _tracking_execute  # type: ignore[assignment]
        conn.set_fetchone({"id": 1})

        writer = M13CorrectionWriter()
        entries = [_valid_entry(case_id=f"CASE-{i:03d}") for i in range(3)]
        ids = writer.write_batch(conn, entries)
        assert len(ids) == 3

    def test_write_batch_empty(self) -> None:
        conn = MockConn()
        writer = M13CorrectionWriter()
        assert writer.write_batch(conn, []) == []

    def test_count_total(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"c": 42})
        writer = M13CorrectionWriter()
        assert writer.count_total(conn) == 42

    def test_count_total_none(self) -> None:
        conn = MockConn()
        conn.set_fetchone(None)
        writer = M13CorrectionWriter()
        assert writer.count_total(conn) == 0

    def test_count_by_field(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"c": 5})
        writer = M13CorrectionWriter()
        assert writer.count_by_field(conn, "regime.procedure_type") == 5
        assert conn.last_params == {"field_path": "regime.procedure_type"}

    def test_count_by_case(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"c": 3})
        writer = M13CorrectionWriter()
        assert writer.count_by_case(conn, "CASE-001") == 3
        assert conn.last_params == {"case_id": "CASE-001"}

    def test_get_recent(self) -> None:
        conn = MockConn()
        conn.set_fetchall([{"id": 1}, {"id": 2}])
        writer = M13CorrectionWriter()
        rows = writer.get_recent(conn, limit=10)
        assert len(rows) == 2
        assert conn.last_params == {"limit": 10}

    def test_get_recent_limit_validation(self) -> None:
        conn = MockConn()
        writer = M13CorrectionWriter()
        with pytest.raises(ValueError, match="limit must be >= 1"):
            writer.get_recent(conn, limit=0)

    def test_get_recent_cap(self) -> None:
        conn = MockConn()
        conn.set_fetchall([])
        writer = M13CorrectionWriter()
        writer.get_recent(conn, limit=5000)
        assert conn.last_params == {"limit": _MAX_RECENT_LIMIT}

    def test_rate_last_30d(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"corrections": 10, "cases_corrected": 5})
        writer = M13CorrectionWriter()
        assert writer.rate_last_30d(conn) == 2.0

    def test_rate_last_30d_zero_cases(self) -> None:
        conn = MockConn()
        conn.set_fetchone({"corrections": 0, "cases_corrected": 0})
        writer = M13CorrectionWriter()
        assert writer.rate_last_30d(conn) == 0.0

    def test_rate_last_30d_none_row(self) -> None:
        conn = MockConn()
        conn.set_fetchone(None)
        writer = M13CorrectionWriter()
        assert writer.rate_last_30d(conn) == 0.0


# ── Guard Rails ─────────────────────────────────────────────────


class TestM13CorrectionWriterGuardRails:
    def test_no_update_delete_in_sql(self) -> None:
        writer = M13CorrectionWriter()
        for attr_name in dir(writer):
            val = getattr(writer, attr_name)
            if isinstance(val, str) and (
                "SELECT" in val.upper() or "INSERT" in val.upper()
            ):
                for forbidden in ("UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER"):
                    assert (
                        forbidden not in val.upper()
                    ), f"{attr_name} contains forbidden SQL: {forbidden}"

    def test_sql_constants_are_strings(self) -> None:
        writer = M13CorrectionWriter()
        for attr_name in (
            "_INSERT_SQL",
            "_COUNT_SQL",
            "_COUNT_BY_FIELD_SQL",
            "_COUNT_BY_CASE_SQL",
            "_RECENT_SQL",
            "_RATE_LAST_30D_SQL",
        ):
            assert isinstance(getattr(writer, attr_name), str)
