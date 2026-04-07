"""F6 — signal_engine."""

from __future__ import annotations

from src.services.signal_engine import (
    compute_assessment_signal,
    compute_domain_signal,
    compute_price_signal,
)


class TestAssessmentSignal:
    def test_high_confidence_is_green(self) -> None:
        assert (
            compute_assessment_signal(confidence=0.85, assessment_status="draft")
            == "green"
        )

    def test_medium_confidence_is_yellow(self) -> None:
        assert (
            compute_assessment_signal(confidence=0.65, assessment_status="draft")
            == "yellow"
        )

    def test_low_confidence_is_red(self) -> None:
        assert (
            compute_assessment_signal(confidence=0.30, assessment_status="draft")
            == "red"
        )

    def test_no_data_is_yellow(self) -> None:
        assert compute_assessment_signal(assessment_status="draft") == "yellow"

    def test_green_boundary(self) -> None:
        assert (
            compute_assessment_signal(confidence=0.80, assessment_status="draft")
            == "green"
        )
        assert (
            compute_assessment_signal(confidence=0.79, assessment_status="draft")
            == "yellow"
        )

    def test_yellow_boundary(self) -> None:
        assert (
            compute_assessment_signal(confidence=0.50, assessment_status="draft")
            == "yellow"
        )
        assert (
            compute_assessment_signal(confidence=0.49, assessment_status="draft")
            == "red"
        )


class TestPriceSignal:
    def test_small_delta_green(self) -> None:
        assert compute_price_signal(market_delta_pct=0.10) == "green"

    def test_medium_delta_yellow(self) -> None:
        assert compute_price_signal(market_delta_pct=0.20) == "yellow"

    def test_large_delta_bell(self) -> None:
        assert compute_price_signal(market_delta_pct=0.35) == "bell"

    def test_negative_delta_uses_absolute(self) -> None:
        assert compute_price_signal(market_delta_pct=-0.10) == "green"


class TestDomainSignal:
    def test_all_green(self) -> None:
        assert compute_domain_signal(["green", "green", "green"]) == "green"

    def test_one_red_makes_red(self) -> None:
        assert compute_domain_signal(["green", "red", "green"]) == "red"

    def test_empty_is_yellow(self) -> None:
        assert compute_domain_signal([]) == "yellow"
