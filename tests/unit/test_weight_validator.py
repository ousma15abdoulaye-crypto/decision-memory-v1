"""F7 — weight_validator (mock conn)."""

from __future__ import annotations

from typing import Any

import pytest

from src.services.weight_validator import validate_criteria_weights


def test_valid_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            "id": "c1",
            "name": "E",
            "critere_nom": None,
            "weight": 0,
            "is_eliminatory": True,
        },
        {
            "id": "c2",
            "name": "A",
            "critere_nom": None,
            "weight": 60,
            "is_eliminatory": False,
        },
        {
            "id": "c3",
            "name": "B",
            "critere_nom": None,
            "weight": 40,
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
            "name": "A",
            "critere_nom": None,
            "weight": 60,
            "is_eliminatory": False,
        },
        {
            "id": "c2",
            "name": "B",
            "critere_nom": None,
            "weight": 30,
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
