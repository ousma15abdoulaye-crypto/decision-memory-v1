"""INV-W06 — pas de champs kill-list dans les payloads M16 (sérialisation)."""

from __future__ import annotations

import json

from src.schemas.m16 import CriterionAssessmentOut, M16EvaluationFrameOut, TargetType

_FORBIDDEN = (
    "winner",
    "rank",
    "recommendation",
    "selected_vendor",
    "best_offer",
)


def test_frame_serializes_without_forbidden_keys() -> None:
    m = M16EvaluationFrameOut(
        workspace_id="w",
        target_type=TargetType.workspace,
        target_id="w",
        domains=[],
        assessments=[
            CriterionAssessmentOut(
                id="a",
                workspace_id="w",
                bundle_id="b",
                criterion_key="k",
                cell_json={},
                assessment_status="draft",
                signal="green",
            )
        ],
        price_lines=[],
        price_values=[],
        bundle_weighted_totals={"b": 12.5},
        weight_validation={"valid": True, "weighted_sum": 100.0, "errors": []},
    )
    raw = json.dumps(json.loads(m.model_dump_json()))
    low = raw.lower()
    for w in _FORBIDDEN:
        assert w not in low
