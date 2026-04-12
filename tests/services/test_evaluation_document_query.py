"""ADR-0017 P5 — ordre SQL unique pour le dernier evaluation_document."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.evaluation_document_query import (
    LATEST_EVALUATION_DOCUMENT_ORDER_CLAUSE,
    fetch_latest_evaluation_document_for_workspace,
)


def test_order_clause_contains_version_and_created_at() -> None:
    assert "version" in LATEST_EVALUATION_DOCUMENT_ORDER_CLAUSE.lower()
    assert "created_at" in LATEST_EVALUATION_DOCUMENT_ORDER_CLAUSE.lower()


@patch("src.services.evaluation_document_query.db_execute_one")
def test_fetch_delegates_to_db_execute_one(mock_one: MagicMock) -> None:
    mock_one.return_value = {"id": "e1", "scores_matrix": {}}
    conn = object()
    out = fetch_latest_evaluation_document_for_workspace(
        conn, "550e8400-e29b-41d4-a716-446655440000"
    )
    assert out == mock_one.return_value
    mock_one.assert_called_once()
    call_sql = mock_one.call_args[0][1]
    assert LATEST_EVALUATION_DOCUMENT_ORDER_CLAUSE.strip() in call_sql.replace(
        "\n", " "
    )
    assert "CAST(:ws AS uuid)" in call_sql
