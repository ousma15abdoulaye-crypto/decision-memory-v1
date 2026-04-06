from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.m16 import CriterionAssessmentOut, M16InitializeResult, TargetType


def test_target_type_values() -> None:
    assert TargetType.workspace.value == "workspace"


def test_criterion_assessment_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        CriterionAssessmentOut(
            id="x",
            workspace_id="w",
            bundle_id="b",
            criterion_key="k",
            assessment_status="draft",
            extra_field=1,  # type: ignore[call-arg]
        )


def test_m16_initialize_result() -> None:
    r = M16InitializeResult(
        workspace_id="w1",
        inserted=2,
        skipped_existing=1,
        skipped_unknown_bundle=0,
        evaluation_document_id="ed1",
    )
    assert r.inserted == 2
