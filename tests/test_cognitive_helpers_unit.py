"""Tests unitaires cognitive_helpers (mocks — sans Postgres)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.api import cognitive_helpers as ch


def test_map_committee_session_row_none() -> None:
    r = ch.map_committee_session_row(None)
    assert r["status"] == "no_session"
    assert r["session_id"] is None


def test_map_committee_session_row_active_maps_to_draft() -> None:
    r = ch.map_committee_session_row(
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "session_status": "active",
            "activated_at": None,
            "sealed_at": None,
        }
    )
    assert r["status"] == "draft"


def test_map_committee_session_row_in_deliberation() -> None:
    r = ch.map_committee_session_row(
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "session_status": "in_deliberation",
            "activated_at": "t",
            "sealed_at": None,
        }
    )
    assert r["status"] == "in_deliberation"


@patch.object(ch, "db_execute_one")
def test_confidence_summary_no_rows_uses_zero(mock_one: MagicMock) -> None:
    mock_one.return_value = None
    conn = MagicMock()
    out = ch.confidence_summary_for_workspace(conn, "ws-1")
    assert out["overall"] == 0.0
    assert out["regime"] == "red"


@patch.object(ch, "db_execute_one")
def test_confidence_summary_min_present_green(mock_one: MagicMock) -> None:
    mock_one.return_value = {"mn": 0.9}
    conn = MagicMock()
    out = ch.confidence_summary_for_workspace(conn, "ws-1")
    assert out["overall"] == 0.9
    assert out["regime"] == "green"
    assert out["display_warning"] is None


@patch.object(ch, "db_execute_one")
def test_confidence_summary_yellow_warning(mock_one: MagicMock) -> None:
    mock_one.return_value = {"mn": 0.65}
    conn = MagicMock()
    out = ch.confidence_summary_for_workspace(conn, "ws-1")
    assert out["regime"] == "yellow"
    assert out["display_warning"] is not None


@patch.object(ch, "db_execute_one", side_effect=RuntimeError("db down"))
def test_confidence_summary_db_error_falls_back_zero(mock_one: MagicMock) -> None:
    conn = MagicMock()
    out = ch.confidence_summary_for_workspace(conn, "ws-1")
    assert out["overall"] == 0.0
    assert out["regime"] == "red"
