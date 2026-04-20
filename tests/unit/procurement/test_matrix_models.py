"""Tests contrat P3.4 — MatrixRow / MatrixSummary (E1)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.procurement.matrix_models import (
    FORBIDDEN_MATRIX_SUMMARY_FIELDS,
    CohortComparabilityStatus,
    ComparabilityStatus,
    EligibilityStatus,
    MatrixRow,
    MatrixRowExplainability,
    MatrixSummary,
    RankStatus,
    TechnicalThresholdMode,
)


def _wid() -> UUID:
    return UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _bid() -> UUID:
    return UUID("bbbbbbbb-cccc-dddd-eeee-ffffffffffff")


def _run() -> UUID:
    return UUID("cccccccc-dddd-eeee-ffff-000000000001")


def test_valid_eligible_ranked_row() -> None:
    rid = _run()
    row = MatrixRow(
        workspace_id=_wid(),
        bundle_id=_bid(),
        supplier_name="ACME",
        pipeline_run_id=rid,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        total_comparability_status=ComparabilityStatus.COMPARABLE,
        rank_status=RankStatus.RANKED,
        rank=1,
        technical_score_system=25.0,
        commercial_score_system=40.0,
        sustainability_score_system=10.0,
        total_score_system=75.0,
    )
    assert row.technical_score_effective == 25.0
    assert row.commercial_score_effective == 40.0
    assert row.sustainability_score_effective == 10.0
    assert row.total_score_effective == 75.0
    assert row.matrix_revision_id == rid
    assert row.technical_threshold_mode == TechnicalThresholdMode.MANDATORY


def test_ineligible_row_scores_and_rank() -> None:
    rid = _run()
    row = MatrixRow(
        workspace_id=_wid(),
        bundle_id=_bid(),
        supplier_name="X",
        pipeline_run_id=rid,
        eligibility_status=EligibilityStatus.INELIGIBLE,
        eligibility_reason_codes=["INELIGIBLE:NIF_EXPIRED"],
        total_comparability_status=ComparabilityStatus.NON_COMPARABLE,
        rank_status=RankStatus.EXCLUDED,
        rank=None,
        technical_score_system=None,
        commercial_score_system=None,
        sustainability_score_system=None,
        total_score_system=None,
    )
    assert row.total_score_system is None
    assert row.rank is None
    assert row.rank_status == RankStatus.EXCLUDED


def test_not_comparable_row() -> None:
    rid = _run()
    row = MatrixRow(
        workspace_id=_wid(),
        bundle_id=_bid(),
        supplier_name="Y",
        pipeline_run_id=rid,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        total_comparability_status=ComparabilityStatus.NON_COMPARABLE,
        rank_status=RankStatus.NOT_COMPARABLE,
        rank=None,
        technical_score_system=30.0,
        commercial_score_system=None,
        sustainability_score_system=None,
        total_score_system=None,
    )
    assert row.rank is None
    assert row.rank_status == RankStatus.NOT_COMPARABLE


def test_incomplete_sustainability_row() -> None:
    rid = _run()
    row = MatrixRow(
        workspace_id=_wid(),
        bundle_id=_bid(),
        supplier_name="Z",
        pipeline_run_id=rid,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        total_comparability_status=ComparabilityStatus.INCOMPLETE,
        rank_status=RankStatus.INCOMPLETE,
        rank=None,
        technical_score_system=25.0,
        commercial_score_system=40.0,
        sustainability_score_system=None,
        total_score_system=None,
    )
    assert row.sustainability_score_effective is None
    assert row.rank_status == RankStatus.INCOMPLETE


def test_i1_rejects_ineligible_with_total_score() -> None:
    rid = _run()
    with pytest.raises(ValidationError) as exc:
        MatrixRow(
            workspace_id=_wid(),
            bundle_id=_bid(),
            supplier_name="Bad",
            pipeline_run_id=rid,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            total_comparability_status=ComparabilityStatus.NON_COMPARABLE,
            rank_status=RankStatus.EXCLUDED,
            rank=None,
            total_score_system=42.0,
        )
    assert "I1" in str(exc.value)


def test_i2_rejects_rank_with_not_comparable_status() -> None:
    rid = _run()
    with pytest.raises(ValidationError) as exc:
        MatrixRow(
            workspace_id=_wid(),
            bundle_id=_bid(),
            supplier_name="Bad",
            pipeline_run_id=rid,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            total_comparability_status=ComparabilityStatus.NON_COMPARABLE,
            rank_status=RankStatus.NOT_COMPARABLE,
            rank=1,
            technical_score_system=10.0,
            commercial_score_system=10.0,
            sustainability_score_system=10.0,
            total_score_system=30.0,
        )
    assert "I2" in str(exc.value)


def test_i3_additivity_rejects_inconsistent_total() -> None:
    """I3 / additivité : trois piliers définis ⇒ total_score_system ≈ somme."""
    rid = _run()
    with pytest.raises(ValidationError) as exc:
        MatrixRow(
            workspace_id=_wid(),
            bundle_id=_bid(),
            supplier_name="Bad",
            pipeline_run_id=rid,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            total_comparability_status=ComparabilityStatus.COMPARABLE,
            rank_status=RankStatus.RANKED,
            rank=1,
            technical_score_system=10.0,
            commercial_score_system=10.0,
            sustainability_score_system=10.0,
            total_score_system=100.0,
        )
    msg = str(exc.value)
    assert "I3" in msg or "Additivité" in msg


def test_effective_equals_system_when_no_override() -> None:
    rid = _run()
    row = MatrixRow(
        workspace_id=_wid(),
        bundle_id=_bid(),
        supplier_name="OK",
        pipeline_run_id=rid,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        total_comparability_status=ComparabilityStatus.COMPARABLE,
        rank_status=RankStatus.RANKED,
        rank=1,
        technical_score_system=25.0,
        commercial_score_system=40.0,
        sustainability_score_system=10.0,
        total_score_system=75.0,
    )
    assert row.technical_score_effective == row.technical_score_system


def test_has_any_override_false_p34() -> None:
    rid = _run()
    row = MatrixRow(
        workspace_id=_wid(),
        bundle_id=_bid(),
        supplier_name="OK",
        pipeline_run_id=rid,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        total_comparability_status=ComparabilityStatus.COMPARABLE,
        rank_status=RankStatus.RANKED,
        rank=1,
        technical_score_system=25.0,
        commercial_score_system=40.0,
        sustainability_score_system=10.0,
        total_score_system=75.0,
    )
    assert row.has_any_override is False


def test_matrix_summary_valid() -> None:
    rid = _run()
    mrid = uuid4()
    now = datetime.now(UTC)
    s = MatrixSummary(
        workspace_id=_wid(),
        pipeline_run_id=rid,
        matrix_revision_id=mrid,
        computed_at=now,
        total_bundles=3,
        count_eligible=2,
        count_ineligible=1,
        count_pending=0,
        count_regularization_pending=0,
        count_comparable=2,
        count_non_comparable=0,
        count_incomplete=0,
        count_ranked=2,
        count_excluded=1,
        count_pending_rank=0,
        count_not_comparable_rank=0,
        count_incomplete_rank=0,
        cohort_comparability_status=CohortComparabilityStatus.PARTIALLY_COMPARABLE,
        has_any_critical_flag=False,
        critical_flags_overview={},
        human_review_required_count=0,
        count_rows_with_override=0,
        override_summary_by_reason={},
        essential_criteria_total=5,
        essential_criteria_passed=4,
        essential_criteria_failed=1,
        essential_criteria_pending=0,
    )
    assert (
        s.cohort_comparability_status == CohortComparabilityStatus.PARTIALLY_COMPARABLE
    )


def test_i6_forbidden_fields_absent_on_summary_schema() -> None:
    keys = set(MatrixSummary.model_fields.keys())
    for forbidden in FORBIDDEN_MATRIX_SUMMARY_FIELDS:
        assert forbidden not in keys


def test_enum_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        MatrixRow.model_validate(
            {
                "workspace_id": str(_wid()),
                "bundle_id": str(_bid()),
                "supplier_name": "X",
                "pipeline_run_id": str(_run()),
                "eligibility_status": "NOT_A_REAL_STATUS",
                "total_comparability_status": ComparabilityStatus.COMPARABLE.value,
                "rank_status": RankStatus.RANKED.value,
                "rank": 1,
                "technical_score_system": 25.0,
                "commercial_score_system": 40.0,
                "sustainability_score_system": 10.0,
                "total_score_system": 75.0,
            }
        )


def test_technical_threshold_mode_defaults_mandatory() -> None:
    rid = _run()
    raw = {
        "workspace_id": _wid(),
        "bundle_id": _bid(),
        "supplier_name": "D",
        "pipeline_run_id": rid,
        "eligibility_status": EligibilityStatus.ELIGIBLE,
        "total_comparability_status": ComparabilityStatus.COMPARABLE,
        "rank_status": RankStatus.RANKED,
        "rank": 1,
        "technical_score_system": 25.0,
        "commercial_score_system": 40.0,
        "sustainability_score_system": 10.0,
        "total_score_system": 75.0,
    }
    row = MatrixRow.model_validate(raw)
    assert row.technical_threshold_mode == TechnicalThresholdMode.MANDATORY


def test_matrix_revision_id_defaults_to_pipeline_run_id() -> None:
    rid = _run()
    row = MatrixRow(
        workspace_id=_wid(),
        bundle_id=_bid(),
        supplier_name="E",
        pipeline_run_id=rid,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        total_comparability_status=ComparabilityStatus.COMPARABLE,
        rank_status=RankStatus.RANKED,
        rank=1,
        technical_score_system=25.0,
        commercial_score_system=40.0,
        sustainability_score_system=10.0,
        total_score_system=75.0,
    )
    assert row.matrix_revision_id == rid


def test_evidence_refs_rejects_none() -> None:
    rid = _run()
    with pytest.raises(ValidationError):
        MatrixRow(
            workspace_id=_wid(),
            bundle_id=_bid(),
            supplier_name="F",
            pipeline_run_id=rid,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            total_comparability_status=ComparabilityStatus.COMPARABLE,
            rank_status=RankStatus.RANKED,
            rank=1,
            technical_score_system=25.0,
            commercial_score_system=40.0,
            sustainability_score_system=10.0,
            total_score_system=75.0,
            evidence_refs=None,  # type: ignore[arg-type]
        )


def test_evidence_refs_empty_list_accepted() -> None:
    rid = _run()
    row = MatrixRow(
        workspace_id=_wid(),
        bundle_id=_bid(),
        supplier_name="G",
        pipeline_run_id=rid,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        total_comparability_status=ComparabilityStatus.COMPARABLE,
        rank_status=RankStatus.RANKED,
        rank=1,
        technical_score_system=25.0,
        commercial_score_system=40.0,
        sustainability_score_system=10.0,
        total_score_system=75.0,
        evidence_refs=[],
    )
    assert row.evidence_refs == []


def test_i4_mutual_exclusion() -> None:
    rid = _run()
    with pytest.raises(ValidationError) as exc:
        MatrixRow(
            workspace_id=_wid(),
            bundle_id=_bid(),
            supplier_name="H",
            pipeline_run_id=rid,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            total_comparability_status=ComparabilityStatus.INCOMPLETE,
            rank_status=RankStatus.EXCLUDED,
            rank=None,
        )
    assert "I4" in str(exc.value)


def test_explainability_nested() -> None:
    rid = _run()
    exp = MatrixRowExplainability(
        status_chain=["eligibility.P3.1B"],
        primary_status_source="P3.1B:ELIGIBLE",
        score_breakdown={"technical": {"n": 1}},
        exclusion_path=None,
    )
    row = MatrixRow(
        workspace_id=_wid(),
        bundle_id=_bid(),
        supplier_name="I",
        pipeline_run_id=rid,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        total_comparability_status=ComparabilityStatus.COMPARABLE,
        rank_status=RankStatus.RANKED,
        rank=1,
        technical_score_system=25.0,
        commercial_score_system=40.0,
        sustainability_score_system=10.0,
        total_score_system=75.0,
        explainability=exp,
    )
    assert row.explainability.primary_status_source == "P3.1B:ELIGIBLE"
