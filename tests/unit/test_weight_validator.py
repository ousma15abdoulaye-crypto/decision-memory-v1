"""INV-W03 + INV-W04 — weight_validator tests (mock conn).

Canon V5.1.0 Locking test 3 (INV-W03) + INV-W04.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.services.weight_validator import (
    sort_criteria_evaluation_order,
    validate_criteria_weights,
)


def test_valid_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            "id": "c1",
            "critere_nom": "E",
            "ponderation": 0,
            "is_eliminatory": True,
        },
        {
            "id": "c2",
            "critere_nom": "A",
            "ponderation": 60,
            "is_eliminatory": False,
        },
        {
            "id": "c3",
            "critere_nom": "B",
            "ponderation": 40,
            "is_eliminatory": False,
        },
    ]

    def fake_fetchall(
        conn: Any, sql: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return rows

    monkeypatch.setattr(
        "src.services.weight_validator.db_fetchall",
        fake_fetchall,
    )
    result = validate_criteria_weights(object(), "ws1")
    assert result["valid"] is True
    assert result["weighted_sum"] == 100.0


def test_invalid_sum(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            "id": "c1",
            "critere_nom": "A",
            "ponderation": 60,
            "is_eliminatory": False,
        },
        {
            "id": "c2",
            "critere_nom": "B",
            "ponderation": 30,
            "is_eliminatory": False,
        },
    ]

    def fake_fetchall(
        conn: Any, sql: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return rows

    monkeypatch.setattr(
        "src.services.weight_validator.db_fetchall",
        fake_fetchall,
    )
    result = validate_criteria_weights(object(), "ws1")
    assert result["valid"] is False
    assert result["weighted_sum"] == 90.0


class TestInvW04SortOrder:
    """INV-W04 : éliminatoires évalués avant les pondérés (Canon V5.1.0)."""

    def test_eliminatory_comes_first(self) -> None:
        criteria = [
            {
                "id": "w1",
                "critere_nom": "Prix",
                "ponderation": 60,
                "is_eliminatory": False,
            },
            {
                "id": "e1",
                "critere_nom": "Capacité financière",
                "ponderation": 0,
                "is_eliminatory": True,
            },
            {
                "id": "w2",
                "critere_nom": "Délai",
                "ponderation": 40,
                "is_eliminatory": False,
            },
        ]
        ordered = sort_criteria_evaluation_order(criteria)
        assert ordered[0]["id"] == "e1", "Éliminatoire doit venir en premier"
        assert ordered[1]["id"] == "w1"
        assert ordered[2]["id"] == "w2"

    def test_all_eliminatory(self) -> None:
        criteria = [
            {"id": "e1", "critere_nom": "A", "ponderation": 0, "is_eliminatory": True},
            {"id": "e2", "critere_nom": "B", "ponderation": 0, "is_eliminatory": True},
        ]
        ordered = sort_criteria_evaluation_order(criteria)
        assert len(ordered) == 2
        assert all(c["is_eliminatory"] for c in ordered)

    def test_no_eliminatory(self) -> None:
        criteria = [
            {
                "id": "w1",
                "critere_nom": "A",
                "ponderation": 60,
                "is_eliminatory": False,
            },
            {
                "id": "w2",
                "critere_nom": "B",
                "ponderation": 40,
                "is_eliminatory": False,
            },
        ]
        ordered = sort_criteria_evaluation_order(criteria)
        assert ordered[0]["id"] == "w1"
        assert ordered[1]["id"] == "w2"

    def test_seuil_elimination_counts_as_eliminatory(self) -> None:
        criteria = [
            {
                "id": "w1",
                "critere_nom": "Prix",
                "ponderation": 100,
                "is_eliminatory": None,
                "seuil_elimination": None,
            },
            {
                "id": "e1",
                "critere_nom": "Note min.",
                "ponderation": 0,
                "is_eliminatory": None,
                "seuil_elimination": 50,
            },
        ]
        ordered = sort_criteria_evaluation_order(criteria)
        assert ordered[0]["id"] == "e1"

    def test_empty_list(self) -> None:
        assert sort_criteria_evaluation_order([]) == []
