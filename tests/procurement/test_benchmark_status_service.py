"""Tests — BenchmarkStatusService."""

from __future__ import annotations

from src.procurement.benchmark_status_service import (
    BenchmarkStatus,
    BenchmarkStatusService,
    ModeTransitionProposal,
)


class TestBenchmarkStatus:
    def test_extra_forbid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="extra"):
            BenchmarkStatus(rogue=True)  # type: ignore[call-arg]

    def test_defaults(self) -> None:
        bs = BenchmarkStatus()
        assert bs.total_cases_processed == 0
        assert bs.correction_rate_last_30d == 0.0


class TestModeTransitionProposal:
    def test_extra_forbid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="extra"):
            ModeTransitionProposal(rogue=True)  # type: ignore[call-arg]

    def test_defaults(self) -> None:
        mtp = ModeTransitionProposal()
        assert mtp.current_mode == "bootstrap"
        assert mtp.requires_cto_validation is True


class TestComputeStatus:
    def test_stub_returns_zeros(self) -> None:
        svc = BenchmarkStatusService()
        status = svc.compute_status()
        assert status.total_cases_processed == 0
        assert status.regime_resolution_accuracy == 0.0
        assert status.computed_at != ""

    def test_with_conn_and_writer(self) -> None:
        from src.procurement.m13_correction_writer import M13CorrectionWriter

        svc = BenchmarkStatusService(
            _db_session_factory=None,
            _correction_repo=M13CorrectionWriter(),
        )
        status = svc.compute_status()
        assert isinstance(status, BenchmarkStatus)


class TestEvaluateTransition:
    def test_bootstrap_all_zero(self) -> None:
        svc = BenchmarkStatusService()
        proposal = svc.evaluate_transition()
        assert proposal.current_mode == "bootstrap"
        assert proposal.proposed_mode == "bootstrap"
        assert proposal.transition_eligible is False
        assert len(proposal.blocking_criteria) > 0

    def test_requires_cto(self) -> None:
        svc = BenchmarkStatusService()
        proposal = svc.evaluate_transition()
        assert proposal.requires_cto_validation is True

    def test_thresholds_defined(self) -> None:
        thresholds = BenchmarkStatusService.PRODUCTION_THRESHOLDS
        assert "total_cases_processed" in thresholds
        assert "regime_resolution_accuracy" in thresholds
        assert thresholds["regime_resolution_accuracy"] == 0.90
        assert thresholds["correction_rate_last_30d_max"] == 0.10
