"""P3.4 E3 — câblage pipeline V5 ↔ projection ``MatrixRow`` / ``MatrixSummary`` (stubs unit)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from src.core.models import DAOCriterion
from src.procurement.eligibility_models import EligibilityVerdict, GateOutput
from src.procurement.m14_evaluation_models import (
    EvaluationReport,
    OfferEvaluation,
    TechnicalScore,
)
from src.procurement.matrix_models import (
    CohortComparabilityStatus,
    EligibilityStatus,
    RankStatus,
)
from src.services.matrix_builder_service import build_matrix_rows
from src.services.pipeline_v5_service import (
    PipelineV5Result,
    build_matrix_projection_for_pipeline,
)


def _wid() -> UUID:
    return UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _run_id() -> UUID:
    return UUID("cccccccc-dddd-eeee-ffff-000000000099")


def _vid(n: int) -> str:
    return str(UUID(int=n))


def _verdict(
    vendor_id: str,
    *,
    eligible: bool,
    gate_result: str,
    dominant: str | None = None,
    failing: list[str] | None = None,
) -> EligibilityVerdict:
    return EligibilityVerdict(
        vendor_id=vendor_id,
        eligible=eligible,
        gate_result=gate_result,
        failing_criteria=list(failing or []),
        pending_criteria=[],
        dominant_cause=dominant,
        auto_verified_count=0,
        human_required_count=0,
        total_criteria_count=5,
        verification_coverage_ratio=0.0,
        blocking_verified_ratio=0.0,
        documentary_strength="HIGH",
        priority_score=0,
        priority_reasons=[],
        locked=False,
    )


def _gate_nominal() -> GateOutput:
    v1, v2, v3 = _vid(1), _vid(2), _vid(3)
    ev = datetime.now(tz=UTC)
    return GateOutput(
        workspace_id=str(_wid()),
        lot_id="lot-1",
        evaluated_at=ev,
        eligible_vendor_ids=[v1],
        excluded_vendor_ids=[v2],
        pending_vendor_ids=[v3],
        verdicts={
            v1: _verdict(v1, eligible=True, gate_result="PASS"),
            v2: _verdict(
                v2,
                eligible=False,
                gate_result="FAIL",
                failing=["c1"],
            ),
            v3: _verdict(v3, eligible=False, gate_result="PENDING", dominant="DOC_GAP"),
        },
        review_queue=[],
        total_submitted=3,
        total_eligible=1,
        total_excluded=1,
        total_pending=1,
        total_not_submitted=0,
    )


def _dao_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": "dc1",
            "critere_nom": "T1",
            "ponderation": 50.0,
            "is_eliminatory": False,
            "famille": "technical",
            "created_at": None,
        },
        {
            "id": "dc2",
            "critere_nom": "C1",
            "ponderation": 50.0,
            "is_eliminatory": False,
            "famille": "commercial",
            "created_at": None,
        },
    ]


def _tech(total: float, *, passes: bool, threshold: float = 50.0) -> TechnicalScore:
    return TechnicalScore(
        criteria_scores=[],
        total_weighted_score=total,
        technical_threshold=threshold,
        passes_threshold=passes,
        ponderation_coherence="OK",
    )


def _offer(
    vid_n: int,
    *,
    name: str,
    eligible_gate: bool,
    tech: TechnicalScore | None,
    flags: list[str] | None = None,
) -> OfferEvaluation:
    return OfferEvaluation(
        offer_document_id=_vid(vid_n),
        supplier_name=name,
        technical_score=tech,
        flags=list(flags or []),
        is_eligible=eligible_gate,
    )


def _strip_volatile(rows_dump: list[dict]) -> list[dict]:
    out = []
    for r in rows_dump:
        c = {k: v for k, v in r.items() if k not in ("computed_at",)}
        out.append(c)
    return out


def test_e3_matrix_projection_nominal_three_vendors() -> None:
    g = _gate_nominal()
    v1, v2, v3 = _vid(1), _vid(2), _vid(3)
    report = EvaluationReport(
        case_id="case-x",
        evaluation_method="quality_cost_based",
        offer_evaluations=[
            _offer(
                1,
                name="Alpha",
                eligible_gate=True,
                tech=_tech(40.0, passes=True),
                flags=[
                    "DMS_MATRIX_COMMERCIAL_SCORE=30.0",
                    "DMS_MATRIX_SUSTAINABILITY_SCORE=10.0",
                ],
            ),
            _offer(2, name="Beta", eligible_gate=False, tech=_tech(10.0, passes=False)),
            _offer(
                3,
                name="Gamma",
                eligible_gate=False,
                tech=_tech(20.0, passes=True),
                flags=["DMS_MATRIX_COMMERCIAL_SCORE=20.0", "DMS_MATRIX_SUSTAINABILITY_SCORE=5.0"],
            ),
        ],
    )
    rows, summary, _ = build_matrix_projection_for_pipeline(
        workspace_id=str(_wid()),
        gate_output=g,
        report=report,
        dao_criteria_rows=_dao_rows(),
        technical_threshold_config={"threshold_mode": "MANDATORY"},
        pipeline_run_id=_run_id(),
    )
    assert len(rows) == 3
    by_vid = {str(r.bundle_id): r for r in rows}
    assert by_vid[v1].eligibility_status == EligibilityStatus.ELIGIBLE
    assert by_vid[v1].rank_status == RankStatus.RANKED
    assert by_vid[v1].rank == 1
    assert by_vid[v2].eligibility_status == EligibilityStatus.INELIGIBLE
    assert by_vid[v2].rank_status == RankStatus.EXCLUDED
    assert by_vid[v3].eligibility_status == EligibilityStatus.PENDING
    assert by_vid[v3].rank_status == RankStatus.PENDING
    assert summary.total_bundles == 3
    assert summary.count_eligible == 1
    assert summary.count_ineligible == 1
    assert summary.count_pending == 1


def test_e3_empty_offer_evaluations_not_comparable_summary() -> None:
    g = _gate_nominal()
    report = EvaluationReport(
        case_id="case-x",
        evaluation_method="quality_cost_based",
        offer_evaluations=[],
    )
    rows, summary, _ = build_matrix_projection_for_pipeline(
        workspace_id=str(_wid()),
        gate_output=g,
        report=report,
        dao_criteria_rows=_dao_rows(),
        pipeline_run_id=_run_id(),
    )
    assert rows == []
    assert summary.total_bundles == 0
    assert summary.cohort_comparability_status == CohortComparabilityStatus.NOT_COMPARABLE


def test_e3_gate_output_none_raises() -> None:
    report = EvaluationReport(
        case_id="case-x",
        evaluation_method="quality_cost_based",
        offer_evaluations=[],
    )
    with pytest.raises(ValueError, match="gate_output"):
        build_matrix_projection_for_pipeline(
            workspace_id=str(_wid()),
            gate_output=None,
            report=report,
            dao_criteria_rows=_dao_rows(),
            pipeline_run_id=_run_id(),
        )


def test_e3_pipeline_v5_result_json_roundtrip() -> None:
    g = _gate_nominal()
    report = EvaluationReport(
        case_id="case-x",
        evaluation_method="quality_cost_based",
        offer_evaluations=[
            _offer(
                1,
                name="Alpha",
                eligible_gate=True,
                tech=_tech(40.0, passes=True),
                flags=["DMS_MATRIX_COMMERCIAL_SCORE=30.0", "DMS_MATRIX_SUSTAINABILITY_SCORE=10.0"],
            ),
        ],
    )
    rows, summary, _ = build_matrix_projection_for_pipeline(
        workspace_id=str(_wid()),
        gate_output=g,
        report=report,
        dao_criteria_rows=_dao_rows(),
        pipeline_run_id=_run_id(),
    )
    out = PipelineV5Result(workspace_id=str(_wid()), matrix_rows=rows, matrix_summary=summary)
    raw = out.model_dump_json()
    data = json.loads(raw)
    assert "matrix_rows" in data and len(data["matrix_rows"]) == 1
    assert data["matrix_summary"]["total_bundles"] == 1


def test_e3_technical_threshold_default_flag_on_rows() -> None:
    g = _gate_nominal()
    report = EvaluationReport(
        case_id="case-x",
        evaluation_method="quality_cost_based",
        offer_evaluations=[
            _offer(
                1,
                name="Alpha",
                eligible_gate=True,
                tech=_tech(40.0, passes=True),
                flags=["DMS_MATRIX_COMMERCIAL_SCORE=30.0", "DMS_MATRIX_SUSTAINABILITY_SCORE=10.0"],
            ),
        ],
    )
    rows, _, _ = build_matrix_projection_for_pipeline(
        workspace_id=str(_wid()),
        gate_output=g,
        report=report,
        dao_criteria_rows=_dao_rows(),
        technical_threshold_config=None,
        pipeline_run_id=_run_id(),
    )
    assert all("TECHNICAL_THRESHOLD_MODE_DEFAULT_APPLIED" in r.warning_flags for r in rows)


def test_e3_idempotent_matrix_projection_fixed_run_id() -> None:
    g = _gate_nominal()
    report = EvaluationReport(
        case_id="case-x",
        evaluation_method="quality_cost_based",
        offer_evaluations=[
            _offer(
                1,
                name="Alpha",
                eligible_gate=True,
                tech=_tech(40.0, passes=True),
                flags=["DMS_MATRIX_COMMERCIAL_SCORE=30.0", "DMS_MATRIX_SUSTAINABILITY_SCORE=10.0"],
            ),
        ],
    )
    rid = _run_id()
    a1, s1, r1 = build_matrix_projection_for_pipeline(
        workspace_id=str(_wid()),
        gate_output=g,
        report=report,
        dao_criteria_rows=_dao_rows(),
        technical_threshold_config={"threshold_mode": "MANDATORY"},
        pipeline_run_id=rid,
    )
    a2, s2, r2 = build_matrix_projection_for_pipeline(
        workspace_id=str(_wid()),
        gate_output=g,
        report=report,
        dao_criteria_rows=_dao_rows(),
        technical_threshold_config={"threshold_mode": "MANDATORY"},
        pipeline_run_id=rid,
    )
    assert r1 == r2
    d1 = _strip_volatile([x.model_dump(mode="json") for x in a1])
    d2 = _strip_volatile([x.model_dump(mode="json") for x in a2])
    assert d1 == d2
    assert s1.model_dump(mode="json", exclude={"computed_at"}) == s2.model_dump(
        mode="json", exclude={"computed_at"}
    )


def test_e3_tiebreak_two_eligible_same_total_score_order_by_bundle_id() -> None:
    u_lo = UUID(int=1)
    u_hi = UUID(int=2)
    s_lo, s_hi = str(u_lo), str(u_hi)
    assert s_lo < s_hi
    ev = datetime.now(tz=UTC)
    g = GateOutput(
        workspace_id=str(_wid()),
        lot_id="lot-1",
        evaluated_at=ev,
        eligible_vendor_ids=[s_lo, s_hi],
        excluded_vendor_ids=[],
        pending_vendor_ids=[],
        verdicts={
            s_lo: _verdict(s_lo, eligible=True, gate_result="PASS"),
            s_hi: _verdict(s_hi, eligible=True, gate_result="PASS"),
        },
        review_queue=[],
        total_submitted=2,
        total_eligible=2,
        total_excluded=0,
        total_pending=0,
        total_not_submitted=0,
    )
    fl = ["DMS_MATRIX_COMMERCIAL_SCORE=30.0", "DMS_MATRIX_SUSTAINABILITY_SCORE=10.0"]
    report = EvaluationReport(
        case_id="case-tie",
        evaluation_method="quality_cost_based",
        offer_evaluations=[
            OfferEvaluation(
                offer_document_id=s_lo,
                supplier_name="Lo",
                technical_score=_tech(20.0, passes=True),
                flags=fl,
                is_eligible=True,
            ),
            OfferEvaluation(
                offer_document_id=s_hi,
                supplier_name="Hi",
                technical_score=_tech(20.0, passes=True),
                flags=fl,
                is_eligible=True,
            ),
        ],
    )
    dao = [
        DAOCriterion(
            categorie="technical",
            critere_nom="T1",
            description="d",
            ponderation=50.0,
            type_reponse="numeric",
            seuil_elimination=None,
            ordre_affichage=1,
        ),
        DAOCriterion(
            categorie="commercial",
            critere_nom="C1",
            description="d",
            ponderation=50.0,
            type_reponse="numeric",
            seuil_elimination=None,
            ordre_affichage=2,
        ),
    ]
    rows = build_matrix_rows(_wid(), _run_id(), report.offer_evaluations, g, dao, None)
    ranked = [r for r in rows if r.rank_status == RankStatus.RANKED]
    assert len(ranked) == 2
    by_rank = {r.rank: r.bundle_id for r in ranked}
    assert by_rank[1] == u_lo
    assert by_rank[2] == u_hi


def test_e3_pipeline_v5_result_pre_matrix_fields_preserved() -> None:
    g = _gate_nominal()
    report = EvaluationReport(
        case_id="case-x",
        evaluation_method="quality_cost_based",
        offer_evaluations=[
            _offer(
                1,
                name="Alpha",
                eligible_gate=True,
                tech=_tech(40.0, passes=True),
                flags=["DMS_MATRIX_COMMERCIAL_SCORE=30.0", "DMS_MATRIX_SUSTAINABILITY_SCORE=10.0"],
            ),
        ],
    )
    rows, summary, _ = build_matrix_projection_for_pipeline(
        workspace_id=str(_wid()),
        gate_output=g,
        report=report,
        dao_criteria_rows=_dao_rows(),
        pipeline_run_id=_run_id(),
    )
    out = PipelineV5Result(
        workspace_id=str(_wid()),
        bundle_status_by_bundle_id={"b1": "SCORABLE"},
        offers_submitted_to_m14=["b1", "b2"],
        matrix_participants=[{"bundle_id": "b1", "role": "participant"}],
        excluded_from_matrix=[{"bundle_id": "x", "reason": "ineligible"}],
        matrix_rows=rows,
        matrix_summary=summary,
    )
    assert out.bundle_status_by_bundle_id == {"b1": "SCORABLE"}
    assert out.offers_submitted_to_m14 == ["b1", "b2"]
    assert out.matrix_participants == [{"bundle_id": "b1", "role": "participant"}]
    assert out.excluded_from_matrix == [{"bundle_id": "x", "reason": "ineligible"}]
    assert len(out.matrix_rows) == 1
