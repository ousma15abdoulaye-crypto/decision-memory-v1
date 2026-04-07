"""F1 — enums M16 purs (sans SQLAlchemy)."""

from __future__ import annotations

import importlib
import inspect

from src.models.m16_enums import (
    AssessmentStatus,
    ClarificationStatus,
    DaoScoringMode,
    PriceSignal,
    TargetType,
    ThreadStatus,
)


def test_target_type_values() -> None:
    assert TargetType.workspace.value == "workspace"
    assert TargetType.bundle.value == "bundle"
    assert len(TargetType) == 3


def test_thread_status_values() -> None:
    assert ThreadStatus.open.value == "open"
    assert ThreadStatus.archived.value == "archived"
    assert len(ThreadStatus) == 2


def test_clarification_status_values() -> None:
    assert ClarificationStatus.withdrawn.value == "withdrawn"
    assert len(ClarificationStatus) == 3


def test_assessment_status_values() -> None:
    assert AssessmentStatus.not_applicable.value == "not_applicable"
    assert len(AssessmentStatus) == 5


def test_dao_scoring_mode_values() -> None:
    assert DaoScoringMode.numeric.value == "numeric"
    assert len(DaoScoringMode) == 4


def test_price_signal_values() -> None:
    assert PriceSignal.bell.value == "bell"
    assert len(PriceSignal) == 4


def test_enums_are_str_enum() -> None:
    for e in (
        TargetType,
        ThreadStatus,
        ClarificationStatus,
        AssessmentStatus,
        DaoScoringMode,
        PriceSignal,
    ):
        for member in e:
            assert isinstance(member.value, str)


def test_no_sqlalchemy_import() -> None:
    mod = importlib.import_module("src.models.m16_enums")
    source = inspect.getsource(mod)
    assert "sqlalchemy" not in source.lower()
