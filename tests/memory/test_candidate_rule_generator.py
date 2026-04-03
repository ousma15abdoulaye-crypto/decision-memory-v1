"""Tests — CandidateRuleGenerator."""

from __future__ import annotations

from src.memory.candidate_rule_generator import CandidateRuleGenerator
from src.memory.pattern_models import DetectedPattern, PatternType


def _pattern(
    pt: PatternType = PatternType.correction_cluster,
    field_path: str = "regime.procedure_type",
    occurrences: int = 5,
) -> DetectedPattern:
    return DetectedPattern(
        pattern_type=pt,
        field_path=field_path,
        occurrences=occurrences,
        confidence=0.8,
        description=f"cluster on {field_path}",
        first_seen="2026-01-01",
        last_seen="2026-03-01",
    )


class TestGenerateFromPatterns:
    def test_generates_rule_for_cluster(self) -> None:
        gen = CandidateRuleGenerator()
        rules = gen.generate_from_patterns([_pattern()])
        assert len(rules) == 1
        assert rules[0]["status"] == "proposed"
        assert rules[0]["origin"] == "pattern_detector"
        assert rules[0]["change_type"] == "correction_cluster"
        assert "rule_id" in rules[0]

    def test_skips_non_cluster_patterns(self) -> None:
        gen = CandidateRuleGenerator()
        rules = gen.generate_from_patterns(
            [
                _pattern(pt=PatternType.confidence_drift),
            ]
        )
        assert len(rules) == 0

    def test_multiple_clusters(self) -> None:
        gen = CandidateRuleGenerator()
        rules = gen.generate_from_patterns(
            [
                _pattern(field_path="regime.procedure_type"),
                _pattern(field_path="gate_assembly.fiscal_clearance"),
            ]
        )
        assert len(rules) == 2
        ids = {r["rule_id"] for r in rules}
        assert len(ids) == 2

    def test_empty_input(self) -> None:
        gen = CandidateRuleGenerator()
        assert gen.generate_from_patterns([]) == []

    def test_rule_id_deterministic(self) -> None:
        gen = CandidateRuleGenerator()
        r1 = gen.generate_from_patterns([_pattern()])[0]["rule_id"]
        r2 = gen.generate_from_patterns([_pattern()])[0]["rule_id"]
        assert r1 == r2
