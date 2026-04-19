"""P3.4 E2 — ``matrix_builder_service`` (R1–R9, summary, idempotence)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from src.core.models import DAOCriterion
from src.procurement.eligibility_models import EligibilityVerdict, GateOutput
from src.procurement.m14_evaluation_models import OfferEvaluation, TechnicalScore
from src.procurement.matrix_models import (
    FORBIDDEN_MATRIX_SUMMARY_FIELDS,
    CohortComparabilityStatus,
    EligibilityStatus,
    MatrixSummary,
    RankStatus,
    TechnicalThresholdMode,
)
from src.services.matrix_builder_service import build_matrix_rows, build_matrix_summary


def _wid() -> UUID:
    return UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _run() -> UUID:
    return UUID("cccccccc-dddd-eeee-ffff-000000000001")


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


def _gate(
    *,
    eligible: list[str],
    excluded: list[str],
    pending: list[str],
    verdicts: dict[str, EligibilityVerdict],
    ws: str | None = None,
) -> GateOutput:
    ev = datetime.now(tz=UTC)
    e, x, p = len(eligible), len(excluded), len(pending)
    return GateOutput(
        workspace_id=ws or str(_wid()),
        lot_id="lot-1",
        evaluated_at=ev,
        eligible_vendor_ids=list(eligible),
        excluded_vendor_ids=list(excluded),
        pending_vendor_ids=list(pending),
        verdicts=verdicts,
        review_queue=[],
        total_submitted=e + x + p,
        total_eligible=e,
        total_excluded=x,
        total_pending=p,
        total_not_submitted=0,
    )


def _dao() -> list[DAOCriterion]:
    return [
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


def _tech(
    total: float,
    *,
    passes: bool,
    threshold: float = 50.0,
) -> TechnicalScore:
    return TechnicalScore(
        criteria_scores=[],
        total_weighted_score=total,
        technical_threshold=threshold,
        passes_threshold=passes,
        ponderation_coherence="OK",
    )


def _offer(
    vid: int,
    *,
    name: str = "S",
    eligible_gate: bool,
    tech: TechnicalScore | None,
    flags: list[str] | None = None,
    commercial_flag: str | None = None,
    sust_flag: str | None = None,
) -> OfferEvaluation:
    fl = list(flags or [])
    if commercial_flag:
        fl.append(commercial_flag)
    if sust_flag:
        fl.append(sust_flag)
    return OfferEvaluation(
        offer_document_id=_vid(vid),
        supplier_name=name,
        technical_score=tech,
        flags=fl,
        is_eligible=eligible_gate,
    )


def _dump_stable(rows: list) -> list[dict]:
    out = []
    for r in rows:
        d = r.model_dump(mode="json", exclude={"computed_at"})
        d.pop("technical_score_effective", None)
        d.pop("commercial_score_effective", None)
        d.pop("sustainability_score_effective", None)
        d.pop("total_score_effective", None)
        d.pop("has_any_override", None)
        out.append(d)
    return out


def test_r1_ineligible_excluded_no_scores() -> None:
    vid = 101
    vs = _vid(vid)
    gate = _gate(
        eligible=[],
        excluded=[vs],
        pending=[],
        verdicts={vs: _verdict(vs, eligible=False, gate_result="FAIL", failing=["c1"])},
    )
    rows = build_matrix_rows(
        _wid(),
        _run(),
        [
            _offer(
                vid,
                eligible_gate=False,
                tech=_tech(10.0, passes=True),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=10",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=5",
            )
        ],
        gate,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    assert len(rows) == 1
    r = rows[0]
    assert r.eligibility_status == EligibilityStatus.INELIGIBLE
    assert r.rank_status == RankStatus.EXCLUDED
    assert r.rank is None
    assert r.total_score_system is None


def test_r2_pending_rank_null() -> None:
    vid = 102
    vs = _vid(vid)
    gate = _gate(
        eligible=[],
        excluded=[],
        pending=[vs],
        verdicts={vs: _verdict(vs, eligible=False, gate_result="PENDING", dominant="WEAK_DOCUMENTARY")},
    )
    rows = build_matrix_rows(
        _wid(),
        _run(),
        [_offer(vid, eligible_gate=True, tech=_tech(10.0, passes=True))],
        gate,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    assert rows[0].eligibility_status == EligibilityStatus.PENDING
    assert rows[0].rank is None
    assert rows[0].rank_status == RankStatus.PENDING


def test_r3_regularization_pending_like_pending() -> None:
    vid = 103
    vs = _vid(vid)
    gate = _gate(
        eligible=[],
        excluded=[],
        pending=[vs],
        verdicts={
            vs: _verdict(
                vs,
                eligible=False,
                gate_result="PENDING",
                dominant="PENDING_REGULARIZATION_OR_REVIEW",
            )
        },
    )
    rows = build_matrix_rows(
        _wid(),
        _run(),
        [_offer(vid, eligible_gate=True, tech=_tech(10.0, passes=True))],
        gate,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    assert rows[0].eligibility_status == EligibilityStatus.REGULARIZATION_PENDING
    assert rows[0].rank_status == RankStatus.PENDING


def test_r4_mandatory_not_qualified_excluded() -> None:
    vid = 104
    vs = _vid(vid)
    gate = _gate(
        eligible=[vs],
        excluded=[],
        pending=[],
        verdicts={vs: _verdict(vs, eligible=True, gate_result="PASS")},
    )
    rows = build_matrix_rows(
        _wid(),
        _run(),
        [
            _offer(
                vid,
                eligible_gate=True,
                tech=_tech(10.0, passes=False),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=40",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            )
        ],
        gate,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    r = rows[0]
    assert r.rank_status == RankStatus.EXCLUDED
    assert r.rank is None


def test_r5_informative_not_qualified_still_ranked_with_flag() -> None:
    vid = 105
    vs = _vid(vid)
    gate = _gate(
        eligible=[vs],
        excluded=[],
        pending=[],
        verdicts={vs: _verdict(vs, eligible=True, gate_result="PASS")},
    )
    rows = build_matrix_rows(
        _wid(),
        _run(),
        [
            _offer(
                vid,
                eligible_gate=True,
                tech=_tech(10.0, passes=False),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=40",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            )
        ],
        gate,
        _dao(),
        {"threshold_mode": "INFORMATIVE"},
    )
    r = rows[0]
    assert r.rank_status == RankStatus.RANKED
    assert r.rank == 1
    assert "TECHNICAL_INFORMATIVE_BELOW_THRESHOLD" in r.warning_flags


def test_r6_ranked_order_desc() -> None:
    v1, v2 = 106, 107
    s1, s2 = _vid(v1), _vid(v2)
    gate = _gate(
        eligible=[s1, s2],
        excluded=[],
        pending=[],
        verdicts={
            s1: _verdict(s1, eligible=True, gate_result="PASS"),
            s2: _verdict(s2, eligible=True, gate_result="PASS"),
        },
    )
    rows = build_matrix_rows(
        _wid(),
        _run(),
        [
            _offer(
                v1,
                name="A",
                eligible_gate=True,
                tech=_tech(10.0, passes=True),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=10",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            ),
            _offer(
                v2,
                name="B",
                eligible_gate=True,
                tech=_tech(20.0, passes=True),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=40",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            ),
        ],
        gate,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    by = {str(r.bundle_id): r for r in rows}
    assert by[s2].rank == 1
    assert by[s1].rank == 2


def test_r7_price_ambiguous_not_comparable() -> None:
    vid = 108
    vs = _vid(vid)
    gate = _gate(
        eligible=[vs],
        excluded=[],
        pending=[],
        verdicts={vs: _verdict(vs, eligible=True, gate_result="PASS")},
    )
    rows = build_matrix_rows(
        _wid(),
        _run(),
        [
            _offer(
                vid,
                eligible_gate=True,
                tech=_tech(30.0, passes=True),
                flags=["p33_price_ambiguous"],
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=5",
            )
        ],
        gate,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    r = rows[0]
    assert r.commercial_score_system is None
    assert r.rank_status == RankStatus.NOT_COMPARABLE


def test_r8_sustainability_null_incomplete() -> None:
    vid = 109
    vs = _vid(vid)
    gate = _gate(
        eligible=[vs],
        excluded=[],
        pending=[],
        verdicts={vs: _verdict(vs, eligible=True, gate_result="PASS")},
    )
    rows = build_matrix_rows(
        _wid(),
        _run(),
        [
            _offer(
                vid,
                eligible_gate=True,
                tech=_tech(25.0, passes=True),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=40",
            )
        ],
        gate,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    assert rows[0].sustainability_score_system is None
    assert rows[0].rank_status == RankStatus.INCOMPLETE


def test_r9_cohort_asymmetric_commercial() -> None:
    v1, v2 = 110, 111
    s1, s2 = _vid(v1), _vid(v2)
    gate = _gate(
        eligible=[s1, s2],
        excluded=[],
        pending=[],
        verdicts={
            s1: _verdict(s1, eligible=True, gate_result="PASS"),
            s2: _verdict(s2, eligible=True, gate_result="PASS"),
        },
    )
    rows = build_matrix_rows(
        _wid(),
        _run(),
        [
            _offer(
                v1,
                eligible_gate=True,
                tech=_tech(25.0, passes=True),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=40",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            ),
            _offer(
                v2,
                eligible_gate=True,
                tech=_tech(25.0, passes=True),
                flags=["p33_price_ambiguous"],
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            ),
        ],
        gate,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    assert all(r.rank_status == RankStatus.NOT_COMPARABLE for r in rows)
    assert all(r.rank is None for r in rows)
    assert all("COHORT_ASYMMETRIC_COMMERCIAL" in r.warning_flags for r in rows)


def test_summary_fully_partially_not() -> None:
    w = _wid()
    rid = _run()
    v1, v2, v3 = 201, 202, 203
    a, b, c = _vid(v1), _vid(v2), _vid(v3)

    gate_full = _gate(
        eligible=[a, b],
        excluded=[],
        pending=[],
        verdicts={
            a: _verdict(a, eligible=True, gate_result="PASS"),
            b: _verdict(b, eligible=True, gate_result="PASS"),
        },
    )
    rows_full = build_matrix_rows(
        w,
        rid,
        [
            _offer(
                v1,
                eligible_gate=True,
                tech=_tech(10.0, passes=True),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=40",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            ),
            _offer(
                v2,
                eligible_gate=True,
                tech=_tech(12.0, passes=True),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=30",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            ),
        ],
        gate_full,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    s_full = build_matrix_summary(rows_full, w, rid)
    assert s_full.cohort_comparability_status == CohortComparabilityStatus.FULLY_COMPARABLE

    gate_mix = _gate(
        eligible=[a, b],
        excluded=[c],
        pending=[],
        verdicts={
            a: _verdict(a, eligible=True, gate_result="PASS"),
            b: _verdict(b, eligible=True, gate_result="PASS"),
            c: _verdict(c, eligible=False, gate_result="FAIL"),
        },
    )
    rows_mix = build_matrix_rows(
        w,
        rid,
        [
            _offer(
                v1,
                eligible_gate=True,
                tech=_tech(10.0, passes=True),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=40",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            ),
            _offer(
                v2,
                eligible_gate=True,
                tech=_tech(12.0, passes=True),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=30",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            ),
            _offer(
                v3,
                eligible_gate=False,
                tech=None,
            ),
        ],
        gate_mix,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    s_mix = build_matrix_summary(rows_mix, w, rid)
    assert s_mix.cohort_comparability_status == CohortComparabilityStatus.PARTIALLY_COMPARABLE

    gate_nc = _gate(
        eligible=[a, b],
        excluded=[],
        pending=[],
        verdicts={
            a: _verdict(a, eligible=True, gate_result="PASS"),
            b: _verdict(b, eligible=True, gate_result="PASS"),
        },
    )
    rows_nc = build_matrix_rows(
        w,
        rid,
        [
            _offer(
                v1,
                eligible_gate=True,
                tech=_tech(10.0, passes=True),
                flags=["p33_price_ambiguous"],
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            ),
            _offer(
                v2,
                eligible_gate=True,
                tech=_tech(12.0, passes=True),
                flags=["p33_price_ambiguous"],
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            ),
        ],
        gate_nc,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    s_nc = build_matrix_summary(rows_nc, w, rid)
    assert s_nc.cohort_comparability_status == CohortComparabilityStatus.NOT_COMPARABLE


def test_summary_i6_forbidden_absent() -> None:
    keys = set(MatrixSummary.model_fields.keys())
    for forbidden in FORBIDDEN_MATRIX_SUMMARY_FIELDS:
        assert forbidden not in keys


def test_idempotence_double_build() -> None:
    vid = 301
    vs = _vid(vid)
    gate = _gate(
        eligible=[vs],
        excluded=[],
        pending=[],
        verdicts={vs: _verdict(vs, eligible=True, gate_result="PASS")},
    )
    offers = [
        _offer(
            vid,
            eligible_gate=True,
            tech=_tech(25.0, passes=True),
            commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=40",
            sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
        )
    ]
    a = build_matrix_rows(_wid(), _run(), offers, gate, _dao(), {"threshold_mode": "MANDATORY"})
    b = build_matrix_rows(_wid(), _run(), offers, gate, _dao(), {"threshold_mode": "MANDATORY"})
    assert _dump_stable(a) == _dump_stable(b)


def test_technical_threshold_default_flag() -> None:
    vid = 401
    vs = _vid(vid)
    gate = _gate(
        eligible=[vs],
        excluded=[],
        pending=[],
        verdicts={vs: _verdict(vs, eligible=True, gate_result="PASS")},
    )
    rows = build_matrix_rows(
        _wid(),
        _run(),
        [
            _offer(
                vid,
                eligible_gate=True,
                tech=_tech(25.0, passes=True),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=40",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            )
        ],
        gate,
        _dao(),
        None,
    )
    assert rows[0].technical_threshold_mode == TechnicalThresholdMode.MANDATORY
    assert "TECHNICAL_THRESHOLD_MODE_DEFAULT_APPLIED" in rows[0].warning_flags


def test_explainability_status_chain() -> None:
    vid = 501
    vs = _vid(vid)
    gate = _gate(
        eligible=[vs],
        excluded=[],
        pending=[],
        verdicts={vs: _verdict(vs, eligible=True, gate_result="PASS")},
    )
    rows = build_matrix_rows(
        _wid(),
        _run(),
        [
            _offer(
                vid,
                eligible_gate=True,
                tech=_tech(25.0, passes=True),
                commercial_flag="DMS_MATRIX_COMMERCIAL_SCORE=40",
                sust_flag="DMS_MATRIX_SUSTAINABILITY_SCORE=10",
            )
        ],
        gate,
        _dao(),
        {"threshold_mode": "MANDATORY"},
    )
    ex = rows[0].explainability
    assert ex.status_chain[0] == "eligibility.P3.1B"
    assert ex.status_chain[-1] == "rank.P3.4"
    assert "P3.4" in ex.primary_status_source or "P3." in ex.primary_status_source
