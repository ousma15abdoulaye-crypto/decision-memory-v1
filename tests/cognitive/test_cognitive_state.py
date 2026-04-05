"""Tests BLOC5 — CognitiveState + confiance (sans DB)."""

import pytest

from src.cognitive.cognitive_state import (
    COGNITIVE_STATE_METADATA,
    CognitiveFacts,
    TransitionForbidden,
    compute_cognitive_state,
    describe_cognitive_state,
    validate_transition,
)
from src.cognitive.confidence_envelope import (
    compute_bundle_confidence,
    compute_frame_confidence,
    regime_from_overall,
    requires_hitl,
)


def test_e0_intake_draft_no_package() -> None:
    f = CognitiveFacts(
        workspace_status="draft",
        has_source_package=False,
        bundle_count=0,
        bundles_all_qualified=False,
        evaluation_frame_complete=False,
    )
    assert compute_cognitive_state(f) == "E0"


def test_e1_context_building_draft_with_package() -> None:
    f = CognitiveFacts(
        workspace_status="draft",
        has_source_package=True,
        bundle_count=0,
        bundles_all_qualified=False,
        evaluation_frame_complete=False,
    )
    assert compute_cognitive_state(f) == "E1"


def test_e2_assembly() -> None:
    f = CognitiveFacts(
        workspace_status="assembling",
        has_source_package=True,
        bundle_count=0,
        bundles_all_qualified=False,
        evaluation_frame_complete=False,
    )
    assert compute_cognitive_state(f) == "E2"


def test_e3_qualification_partial() -> None:
    f = CognitiveFacts(
        workspace_status="assembled",
        has_source_package=True,
        bundle_count=2,
        bundles_all_qualified=False,
        evaluation_frame_complete=False,
    )
    assert compute_cognitive_state(f) == "E3"


def test_e4_comparative_all_qualified() -> None:
    f = CognitiveFacts(
        workspace_status="analysis_complete",
        has_source_package=True,
        bundle_count=2,
        bundles_all_qualified=True,
        evaluation_frame_complete=True,
    )
    assert compute_cognitive_state(f) == "E4"


def test_e5_deliberation() -> None:
    f = CognitiveFacts(
        workspace_status="in_deliberation",
        has_source_package=True,
        bundle_count=2,
        bundles_all_qualified=True,
        evaluation_frame_complete=True,
    )
    assert compute_cognitive_state(f) == "E5"


def test_e6_sealed() -> None:
    f = CognitiveFacts(
        workspace_status="sealed",
        has_source_package=True,
        bundle_count=2,
        bundles_all_qualified=True,
        evaluation_frame_complete=True,
    )
    assert compute_cognitive_state(f) == "E6"


def test_e6_closed_and_cancelled() -> None:
    for st in ("closed", "cancelled"):
        f = CognitiveFacts(
            workspace_status=st,
            has_source_package=False,
            bundle_count=0,
            bundles_all_qualified=False,
            evaluation_frame_complete=False,
        )
        assert compute_cognitive_state(f) == "E6"


def test_edge_unknown_status_defaults_e0() -> None:
    f = CognitiveFacts(
        workspace_status="unknown_future",
        has_source_package=False,
        bundle_count=0,
        bundles_all_qualified=False,
        evaluation_frame_complete=False,
    )
    assert compute_cognitive_state(f) == "E0"


def test_validate_sealed_from_wrong_source_raises() -> None:
    facts = CognitiveFacts(
        workspace_status="analysis_complete",
        has_source_package=True,
        bundle_count=1,
        bundles_all_qualified=True,
        evaluation_frame_complete=True,
    )
    with pytest.raises(TransitionForbidden):
        validate_transition("analysis_complete", "sealed", facts)


def test_describe_cognitive_state_known() -> None:
    d = describe_cognitive_state("E0")
    assert d["phase"] == "intake"
    assert d["state_id"] == "E0"
    assert "E0" in COGNITIVE_STATE_METADATA


def test_validate_sealed_ok_from_deliberation() -> None:
    facts = CognitiveFacts(
        workspace_status="in_deliberation",
        has_source_package=True,
        bundle_count=1,
        bundles_all_qualified=True,
        evaluation_frame_complete=True,
    )
    validate_transition("in_deliberation", "sealed", facts)


def test_bundle_confidence_empty_is_zero() -> None:
    assert compute_bundle_confidence([]) == 0.0


def test_frame_confidence_empty_is_zero() -> None:
    assert compute_frame_confidence([]) == 0.0


def test_regime_and_hitl() -> None:
    assert regime_from_overall(0.85) == "green"
    assert regime_from_overall(0.6) == "yellow"
    assert regime_from_overall(0.2) == "red"
    assert requires_hitl(0.2) is True
    assert requires_hitl(0.9) is False
