"""Tests for src/procurement/document_validity_rules.py — L5 validity judgment."""

from __future__ import annotations

from src.procurement.document_validity_rules import compute_validity
from src.procurement.procedure_models import PartDetectionResult


def _make_detected(name: str) -> PartDetectionResult:
    return PartDetectionResult(
        part_name=name,
        detection_level="level_1_heading",
        confidence=0.90,
        evidence=["test"],
    )


def _make_missing(name: str) -> PartDetectionResult:
    return PartDetectionResult(
        part_name=name,
        detection_level="not_detected",
        confidence=0.0,
        evidence=["no_match"],
    )


class TestComputeValidity:
    def test_all_detected_is_valid(self) -> None:
        parts = [_make_detected("a"), _make_detected("b")]
        v = compute_validity(parts, ["opt1"], [], "tdr")
        assert v.document_validity_status.value == "valid"
        assert v.mandatory_coverage == 1.0

    def test_none_detected_is_invalid(self) -> None:
        parts = [_make_missing("a"), _make_missing("b")]
        v = compute_validity(parts, [], [], "tdr")
        assert v.document_validity_status.value == "invalid"
        assert v.mandatory_coverage == 0.0

    def test_partial_detection(self) -> None:
        parts = [_make_detected("a"), _make_missing("b")]
        v = compute_validity(parts, [], [], "tdr")
        assert v.document_validity_status.value == "partial"
        assert 0.0 < v.mandatory_coverage < 1.0

    def test_ocr_failed_is_not_assessable(self) -> None:
        parts = [_make_detected("a")]
        v = compute_validity(parts, [], [], "tdr", quality_class="ocr_failed")
        assert v.document_validity_status.value == "not_assessable"

    def test_unknown_kind_is_not_assessable(self) -> None:
        parts = [_make_detected("a")]
        v = compute_validity(parts, [], [], "unknown")
        assert v.document_validity_status.value == "not_assessable"

    def test_degraded_caps_confidence(self) -> None:
        parts = [_make_detected("a"), _make_detected("b")]
        v = compute_validity(parts, [], [], "tdr", quality_class="degraded")
        assert v.document_validity_status.confidence <= 0.60

    def test_empty_parts_not_assessable(self) -> None:
        v = compute_validity([], [], [], "tdr")
        assert v.document_validity_status.value == "not_assessable"
