"""Tests unitaires — CognitiveStateResult V5.1.0 (INV-C01 à INV-C04).

Canon V5.1.0 Section O3.
"""

from __future__ import annotations

import pytest

from src.cognitive.cognitive_state import (
    CognitiveFacts,
    CognitiveStateResult,
    compute_cognitive_state,
    compute_cognitive_state_result,
)


def _facts(
    status: str = "draft",
    has_source: bool = False,
    bundle_count: int = 0,
    all_qualified: bool = False,
    frame_complete: bool = False,
) -> CognitiveFacts:
    return CognitiveFacts(
        workspace_status=status,
        has_source_package=has_source,
        bundle_count=bundle_count,
        bundles_all_qualified=all_qualified,
        evaluation_frame_complete=frame_complete,
    )


class TestCognitiveStateResultType:
    def test_returns_cognitive_state_result(self):
        result = compute_cognitive_state_result(_facts())
        assert isinstance(result, CognitiveStateResult)

    def test_state_matches_compute_cognitive_state(self):
        facts = _facts()
        state_str = compute_cognitive_state(facts)
        result = compute_cognitive_state_result(facts)
        assert result.state == state_str

    def test_label_fr_not_empty(self):
        for status in (
            "draft",
            "assembling",
            "in_analysis",
            "in_deliberation",
            "sealed",
        ):
            result = compute_cognitive_state_result(_facts(status=status))
            assert result.label_fr, f"label_fr vide pour status={status}"


class TestCompletenessValues:
    def test_e0_completeness(self):
        result = compute_cognitive_state_result(_facts("draft", has_source=False))
        assert result.state == "E0"
        assert result.completeness == 0.0

    def test_e6_completeness(self):
        result = compute_cognitive_state_result(_facts("sealed"))
        assert result.state == "E6"
        assert result.completeness == 1.0

    def test_completeness_increases_monotonically(self):
        states_facts = [
            _facts("draft", has_source=False),
            _facts("draft", has_source=True),
            _facts("assembling"),
            _facts("in_analysis", bundle_count=2, all_qualified=False),
            _facts(
                "in_analysis", bundle_count=2, all_qualified=True, frame_complete=True
            ),
            _facts("in_deliberation"),
            _facts("sealed"),
        ]
        completeness_values = [
            compute_cognitive_state_result(f).completeness for f in states_facts
        ]
        for i in range(len(completeness_values) - 1):
            assert completeness_values[i] <= completeness_values[i + 1]


class TestCanAdvanceAndBlockers:
    def test_e0_no_source_cannot_advance(self):
        result = compute_cognitive_state_result(_facts("draft", has_source=False))
        assert not result.can_advance
        assert len(result.advance_blockers) > 0

    def test_e0_with_source_can_advance(self):
        result = compute_cognitive_state_result(_facts("draft", has_source=True))
        assert result.can_advance
        assert len(result.advance_blockers) == 0

    def test_e3_unqualified_cannot_advance(self):
        result = compute_cognitive_state_result(
            _facts("in_analysis", bundle_count=2, all_qualified=False)
        )
        assert result.state == "E3"
        assert not result.can_advance
        assert any("qualifi" in b.lower() for b in result.advance_blockers)

    def test_e6_cannot_advance(self):
        result = compute_cognitive_state_result(_facts("sealed"))
        assert not result.can_advance

    def test_advance_blockers_in_french(self):
        result = compute_cognitive_state_result(_facts("draft", has_source=False))
        for blocker in result.advance_blockers:
            assert blocker  # not empty
            assert isinstance(blocker, str)


class TestAvailableActions:
    def test_agent_query_in_all_states(self):
        for status in (
            "draft",
            "assembling",
            "in_analysis",
            "in_deliberation",
            "sealed",
        ):
            result = compute_cognitive_state_result(_facts(status))
            assert "agent.query" in result.available_actions

    def test_committee_seal_in_e5(self):
        result = compute_cognitive_state_result(_facts("in_deliberation"))
        assert result.state == "E5"
        assert "committee.seal" in result.available_actions

    def test_workspace_manage_not_in_e6(self):
        result = compute_cognitive_state_result(_facts("sealed"))
        assert "workspace.manage" not in result.available_actions

    def test_pv_read_in_e6(self):
        result = compute_cognitive_state_result(_facts("sealed"))
        assert "pv.read" in result.available_actions


class TestConfidenceRegime:
    def test_e6_green(self):
        result = compute_cognitive_state_result(_facts("sealed"))
        assert result.confidence_regime == "green"

    def test_e0_red(self):
        result = compute_cognitive_state_result(_facts("draft"))
        assert result.confidence_regime == "red"

    def test_regime_is_valid_value(self):
        for status in (
            "draft",
            "assembling",
            "in_analysis",
            "in_deliberation",
            "sealed",
        ):
            result = compute_cognitive_state_result(_facts(status))
            assert result.confidence_regime in ("red", "amber", "green")


class TestBackwardCompatibility:
    """Vérifie que compute_cognitive_state retourne toujours un str."""

    def test_returns_string(self):
        assert isinstance(compute_cognitive_state(_facts()), str)

    @pytest.mark.parametrize(
        "facts,expected",
        [
            (_facts("draft", has_source=False), "E0"),
            (_facts("draft", has_source=True), "E1"),
            (_facts("assembling"), "E2"),
            (_facts("in_deliberation"), "E5"),
            (_facts("sealed"), "E6"),
        ],
    )
    def test_string_values_unchanged(self, facts, expected):
        assert compute_cognitive_state(facts) == expected
