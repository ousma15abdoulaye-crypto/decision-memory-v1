"""
Tests for CaseMemoryWriter — H0.4 deliverable.

Uses MockConn pattern identical to test_m12_correction_writer.py.
No real DB — tests model validation, SQL correctness, builder logic.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest

from src.annotation.memory.case_memory_writer import (
    CaseMemoryEntry,
    CaseMemoryWriter,
    build_from_m12_output,
)

# ── Mock connection ──────────────────────────────────────────────


class MockConn:
    """Minimal mock matching _MemoryConnection protocol."""

    def __init__(self, fetchone_result: dict[str, Any] | None = None):
        self.last_sql: str | None = None
        self.last_params: dict[str, Any] | None = None
        self.call_count = 0
        self._fetchone_result = fetchone_result or {"id": str(uuid4())}

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        self.last_sql = sql
        self.last_params = params
        self.call_count += 1

    def fetchone(self) -> dict[str, Any] | None:
        return self._fetchone_result


# ── CaseMemoryEntry tests ───────────────────────────────────────


class TestCaseMemoryEntry:
    def test_valid_entry(self) -> None:
        entry = CaseMemoryEntry(
            case_id="CASE-001",
            documents_count=3,
            document_kinds=["dao", "offer_technical"],
            framework_detected="SCI",
            framework_confidence=0.8,
            procurement_family="goods",
            m12_confidence_avg=0.8,
            m12_confidence_min=0.6,
        )
        assert entry.case_id == "CASE-001"
        assert entry.documents_count == 3

    def test_extra_forbidden(self) -> None:
        with pytest.raises(Exception):
            CaseMemoryEntry(
                case_id="CASE-001",
                documents_count=1,
                document_kinds=["dao"],
                framework_detected="SCI",
                framework_confidence=0.8,
                procurement_family="goods",
                m12_confidence_avg=0.8,
                m12_confidence_min=0.6,
                rogue_field="nope",
            )

    def test_case_id_min_length(self) -> None:
        with pytest.raises(Exception):
            CaseMemoryEntry(
                case_id="",
                documents_count=0,
                document_kinds=[],
                framework_detected="UNKNOWN",
                framework_confidence=0.6,
                procurement_family="unknown",
                m12_confidence_avg=0.6,
                m12_confidence_min=0.6,
            )

    def test_confidence_bounds(self) -> None:
        with pytest.raises(Exception):
            CaseMemoryEntry(
                case_id="C",
                documents_count=0,
                document_kinds=[],
                framework_detected="SCI",
                framework_confidence=1.5,
                procurement_family="goods",
                m12_confidence_avg=0.8,
                m12_confidence_min=0.6,
            )

    def test_serialisation_roundtrip(self) -> None:
        entry = CaseMemoryEntry(
            case_id="CASE-RT",
            documents_count=2,
            document_kinds=["dao"],
            framework_detected="SCI",
            framework_confidence=0.8,
            procurement_family="works",
            m12_confidence_avg=0.8,
            m12_confidence_min=0.6,
        )
        payload = json.loads(entry.model_dump_json())
        rebuilt = CaseMemoryEntry.model_validate(payload)
        assert rebuilt.case_id == entry.case_id
        assert rebuilt.framework_detected == "SCI"


# ── build_from_m12_output tests ─────────────────────────────────


class TestBuildFromM12Output:
    def test_minimal_output(self) -> None:
        entry = build_from_m12_output("C-1", {})
        assert entry.case_id == "C-1"
        assert entry.documents_count == 0
        assert entry.framework_detected == "UNKNOWN"
        assert entry.procurement_family == "unknown"
        assert entry.m12_confidence_avg == 0.6
        assert entry.m12_confidence_min == 0.6

    def test_full_output(self) -> None:
        m12 = {
            "documents": [
                {"document_kind": "dao", "subtype": "national"},
                {"document_kind": "offer_technical", "subtype": "standard"},
                {"document_kind": "dao"},
            ],
            "framework": {
                "name": "SCI",
                "confidence": 0.9,
                "alternatives": ["DGMP"],
            },
            "procurement_family": "goods",
            "estimated_value": 50000.0,
            "currency": "XOF",
            "zone_scope": ["bamako", "sikasso"],
            "suppliers_detected": ["Vendor A", "Vendor B"],
            "buyer_detected": "SCI Mali",
            "procedure_reference": "REF-2025-001",
            "links": [
                {"status": "resolved"},
                {"status": "unresolved"},
            ],
            "confidences": [0.9, 0.8, 0.6],
            "review_flags": ["low_confidence"],
        }
        entry = build_from_m12_output("C-FULL", m12)
        assert entry.case_id == "C-FULL"
        assert entry.documents_count == 3
        assert "dao" in entry.document_kinds
        assert entry.framework_detected == "SCI"
        assert entry.framework_confidence == 0.9
        assert entry.other_frameworks == ["DGMP"]
        assert entry.procurement_family == "goods"
        assert entry.estimated_value == 50000.0
        assert entry.currency == "XOF"
        assert entry.links_count == 2
        assert entry.unresolved_count == 1
        assert abs(entry.m12_confidence_avg - 0.7666666) < 0.01
        assert entry.m12_confidence_min == 0.6
        assert entry.review_flags == ["low_confidence"]

    def test_deduplicates_doc_kinds(self) -> None:
        m12 = {
            "documents": [
                {"document_kind": "dao"},
                {"document_kind": "dao"},
            ],
        }
        entry = build_from_m12_output("C-DUP", m12)
        assert entry.document_kinds == ["dao"]

    def test_handles_none_framework(self) -> None:
        entry = build_from_m12_output("C-NF", {"framework": None})
        assert entry.framework_detected == "UNKNOWN"
        assert entry.framework_confidence == 0.6


# ── CaseMemoryWriter tests ──────────────────────────────────────


class TestCaseMemoryWriter:
    def test_write_returns_id(self) -> None:
        conn = MockConn({"id": "abc-123"})
        writer = CaseMemoryWriter()
        entry = CaseMemoryEntry(
            case_id="C-W",
            documents_count=1,
            document_kinds=["dao"],
            framework_detected="SCI",
            framework_confidence=0.8,
            procurement_family="goods",
            m12_confidence_avg=0.8,
            m12_confidence_min=0.6,
        )
        result = writer.write(conn, entry)
        assert result == "abc-123"
        assert conn.call_count == 1
        assert "INSERT INTO memory_entries" in conn.last_sql
        assert conn.last_params["cid"] == "C-W"
        assert conn.last_params["etype"] == "case_summary"

    def test_write_content_is_valid_json(self) -> None:
        conn = MockConn({"id": "x"})
        writer = CaseMemoryWriter()
        entry = CaseMemoryEntry(
            case_id="C-JSON",
            documents_count=0,
            document_kinds=[],
            framework_detected="DGMP",
            framework_confidence=0.8,
            procurement_family="works",
            m12_confidence_avg=0.8,
            m12_confidence_min=0.8,
        )
        writer.write(conn, entry)
        content = json.loads(conn.last_params["content"])
        assert content["case_id"] == "C-JSON"
        assert content["framework_detected"] == "DGMP"

    def test_write_raises_on_no_returning(self) -> None:
        conn = MockConn(None)
        conn._fetchone_result = None
        writer = CaseMemoryWriter()
        entry = CaseMemoryEntry(
            case_id="C-FAIL",
            documents_count=0,
            document_kinds=[],
            framework_detected="SCI",
            framework_confidence=0.6,
            procurement_family="unknown",
            m12_confidence_avg=0.6,
            m12_confidence_min=0.6,
        )
        with pytest.raises(RuntimeError, match="UPSERT did not RETURNING id"):
            writer.write(conn, entry)

    def test_get_latest_returns_entry(self) -> None:
        payload = CaseMemoryEntry(
            case_id="C-GL",
            documents_count=2,
            document_kinds=["dao"],
            framework_detected="SCI",
            framework_confidence=0.8,
            procurement_family="goods",
            m12_confidence_avg=0.8,
            m12_confidence_min=0.6,
        )
        conn = MockConn(
            {
                "id": "row-1",
                "case_id": "C-GL",
                "entry_type": "case_summary",
                "content_json": payload.model_dump_json(),
                "created_at": "2026-04-03T10:00:00+00:00",
            }
        )
        writer = CaseMemoryWriter()
        result = writer.get_latest(conn, "C-GL")
        assert result is not None
        assert result.case_id == "C-GL"
        assert result.framework_detected == "SCI"

    def test_get_latest_returns_none(self) -> None:
        conn = MockConn()
        conn._fetchone_result = None
        writer = CaseMemoryWriter()
        result = writer.get_latest(conn, "MISSING")
        assert result is None

    def test_count_total(self) -> None:
        conn = MockConn({"c": 42})
        writer = CaseMemoryWriter()
        assert writer.count_total(conn) == 42

    def test_count_total_zero(self) -> None:
        conn = MockConn(None)
        conn._fetchone_result = None
        writer = CaseMemoryWriter()
        assert writer.count_total(conn) == 0

    def test_no_update_delete_in_sql(self) -> None:
        """Writer must never contain UPDATE/DELETE/DROP/TRUNCATE/ALTER in SQL."""
        import inspect

        source = inspect.getsource(CaseMemoryWriter)
        forbidden = ["UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER"]
        for kw in forbidden:
            occurrences = source.upper().count(kw)
            if kw == "UPDATE":
                assert occurrences <= 1, (
                    f"Found {occurrences} occurrences of {kw} — "
                    "only the ON CONFLICT DO UPDATE is allowed"
                )
            else:
                assert occurrences == 0, f"Found forbidden keyword {kw} in writer"
