"""Tests unitaires P3.1 — EligibilityGate (mandat 16 avril 2026)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.procurement.eligibility_gate import (
    evaluate_vendor,
    null_scores_for_ineligible,
    require_eligible_vendors_or_raise,
    run_eligibility_gate,
    standard_sci_essential_criteria,
)
from src.procurement.eligibility_models import (
    EssentialCriterion,
    VendorGateInput,
)
from src.services.pipeline_v5_service import PipelineError


def _all_hits() -> dict[str, list[str]]:
    return {
        "sci_q1": ["q1_cg"],
        "sci_q2": ["q2_iapg"],
        "sci_q3": ["q3_dual_use"],
        "sci_q4": ["q4_sanctions"],
        "sci_q5_1": ["q5_addr"],
        "sci_q5_2": ["q5_nif"],
        "sci_q5_3": ["q5_rccm"],
        "sci_q5_4": ["q5_non_faillite"],
        "sci_q5_5": ["q5_quitus"],
    }


def test_pass_confirmed_when_all_docs_present() -> None:
    v = VendorGateInput(
        vendor_id="v1",
        vendor_name="ACME",
        has_exploitable_documents=True,
        signal_hits=_all_hits(),
    )
    out = run_eligibility_gate("ws", "lot1", {"v1": v})
    assert out.eligible_vendor_ids == ["v1"]
    assert out.verdicts["v1"].gate_result == "PASS"
    assert out.verdicts["v1"].eligible is True
    assert out.verdicts["v1"].failing_criteria == []


def test_pass_declared_when_declaration_only() -> None:
    crit = EssentialCriterion(
        criterion_id="decl_only",
        question_number="QX",
        label="Politique déclarative test",
        criterion_type="POLICY",
        is_parent=False,
        parent_id=None,
        evidence_expected=[],
        auto_checkable=True,
        verification_source="VENDOR_DECLARATION",
        gate_severity="BLOCKING",
    )
    v = VendorGateInput(
        vendor_id="v1",
        vendor_name="ACME",
        has_exploitable_documents=True,
        vendor_declaration_acceptance={"decl_only": True},
    )
    det = evaluate_vendor(v, [crit])
    r = det.criterion_results["decl_only"]
    assert r.result_internal == "PASS_DECLARED"
    assert r.proof_level == "DECLARATION_ONLY"
    assert r.detection_method == "DECLARED_ONLY"


def test_fail_confirmed_blocking_criterion() -> None:
    hits = _all_hits()
    del hits["sci_q2"]
    v = VendorGateInput(
        vendor_id="v1", has_exploitable_documents=True, signal_hits=hits
    )
    out = run_eligibility_gate("ws", "lot1", {"v1": v})
    assert out.verdicts["v1"].gate_result == "FAIL"
    assert "sci_q2" in out.verdicts["v1"].failing_criteria


def test_pending_on_regularizable_criterion() -> None:
    hits = _all_hits()
    del hits["sci_q5_4"]
    v = VendorGateInput(
        vendor_id="v1", has_exploitable_documents=True, signal_hits=hits
    )
    out = run_eligibility_gate("ws", "lot1", {"v1": v})
    assert out.verdicts["v1"].gate_result == "PENDING"
    assert "sci_q5_4" in out.verdicts["v1"].pending_criteria


def test_not_submitted_vendor() -> None:
    v = VendorGateInput(vendor_id="v1", has_exploitable_documents=False)
    out = run_eligibility_gate("ws", "lot1", {"v1": v})
    assert out.verdicts["v1"].dominant_cause == "NOT_SUBMITTED"
    assert out.verdicts["v1"].gate_result == "FAIL"


def test_q5_fail_if_blocking_subcriteria_fail() -> None:
    hits = _all_hits()
    del hits["sci_q5_1"]
    v = VendorGateInput(
        vendor_id="v1", has_exploitable_documents=True, signal_hits=hits
    )
    det = evaluate_vendor(v, standard_sci_essential_criteria())
    assert det.criterion_results["sci_q5"].result_internal == "FAIL_CONFIRMED"


def test_q5_pending_if_only_regularizable_fail() -> None:
    hits = _all_hits()
    del hits["sci_q5_4"]
    del hits["sci_q5_5"]
    v = VendorGateInput(
        vendor_id="v1", has_exploitable_documents=True, signal_hits=hits
    )
    det = evaluate_vendor(v, standard_sci_essential_criteria())
    assert det.criterion_results["sci_q5"].result_internal == "PENDING_REVIEW"


def test_q5_pass_declared_if_only_declarative_missing() -> None:
    decl = EssentialCriterion(
        criterion_id="sci_q5_decl",
        question_number="Q5.D",
        label="Sous-critère déclaratif test",
        criterion_type="POLICY",
        is_parent=False,
        parent_id="sci_q5",
        evidence_expected=[],
        auto_checkable=True,
        verification_source="VENDOR_DECLARATION",
        gate_severity="DECLARATIVE",
    )
    crits = [*standard_sci_essential_criteria(), decl]
    hits = _all_hits()
    v = VendorGateInput(
        vendor_id="v1",
        has_exploitable_documents=True,
        signal_hits=hits,
        vendor_declaration_acceptance={"sci_q5_decl": True},
    )
    det = evaluate_vendor(v, crits)
    assert det.criterion_results["sci_q5"].result_internal == "PASS_DECLARED"


def test_verification_coverage_ratio_computed() -> None:
    v = VendorGateInput(
        vendor_id="v1", has_exploitable_documents=True, signal_hits=_all_hits()
    )
    out = run_eligibility_gate("ws", "lot1", {"v1": v})
    r = out.verdicts["v1"]
    assert 0.0 <= r.verification_coverage_ratio <= 1.0
    assert r.total_criteria_count >= 9


def test_documentary_strength_low_when_mostly_declared() -> None:
    crits = standard_sci_essential_criteria()
    crits = [
        (
            EssentialCriterion(
                criterion_id=c.criterion_id,
                question_number=c.question_number,
                label=c.label,
                criterion_type=c.criterion_type,
                is_parent=c.is_parent,
                parent_id=c.parent_id,
                evidence_expected=list(c.evidence_expected),
                auto_checkable=c.auto_checkable,
                verification_source=(
                    "VENDOR_DECLARATION"
                    if (
                        not c.is_parent
                        and c.criterion_id
                        in {
                            "sci_q1",
                            "sci_q2",
                            "sci_q3",
                            "sci_q4",
                            "sci_q5_1",
                            "sci_q5_2",
                            "sci_q5_3",
                        }
                    )
                    else c.verification_source
                ),
                gate_severity=c.gate_severity,
            )
        )
        for c in crits
    ]
    acc = {
        cid: True
        for cid in (
            "sci_q1",
            "sci_q2",
            "sci_q3",
            "sci_q4",
            "sci_q5_1",
            "sci_q5_2",
            "sci_q5_3",
        )
    }
    hits = {k: v for k, v in _all_hits().items() if k.startswith("sci_q5")}
    v = VendorGateInput(
        vendor_id="v1",
        has_exploitable_documents=True,
        signal_hits=hits,
        vendor_declaration_acceptance=acc,
    )
    out = run_eligibility_gate("ws", "lot1", {"v1": v}, criteria=crits)
    assert out.verdicts["v1"].documentary_strength == "LOW"


def test_priority_score_high_for_uncertain_exclusion() -> None:
    v = VendorGateInput(
        vendor_id="v1",
        has_exploitable_documents=True,
        signal_hits={k: v for k, v in _all_hits().items() if k != "sci_q3"},
        declared_without_proof_by_criterion={"sci_q3": True},
    )
    out = run_eligibility_gate("ws", "lot1", {"v1": v})
    assert out.verdicts["v1"].gate_result == "FAIL"
    assert out.verdicts["v1"].priority_score >= 80


def test_priority_score_elevated_for_top_vendor_weak_proof() -> None:
    crits = standard_sci_essential_criteria()
    crits = [
        (
            EssentialCriterion(
                criterion_id=c.criterion_id,
                question_number=c.question_number,
                label=c.label,
                criterion_type=c.criterion_type,
                is_parent=c.is_parent,
                parent_id=c.parent_id,
                evidence_expected=list(c.evidence_expected),
                auto_checkable=c.auto_checkable,
                verification_source=(
                    "VENDOR_DECLARATION"
                    if c.criterion_id == "sci_q1"
                    else c.verification_source
                ),
                gate_severity=c.gate_severity,
            )
        )
        for c in crits
    ]
    hits = {k: v for k, v in _all_hits().items() if k != "sci_q1"}
    v = VendorGateInput(
        vendor_id="v1",
        vendor_name="StrategicCo",
        is_important_vendor=True,
        has_exploitable_documents=True,
        signal_hits=hits,
        vendor_declaration_acceptance={"sci_q1": True},
    )
    out = run_eligibility_gate("ws", "lot1", {"v1": v}, criteria=crits)
    assert (
        "important_vendor_PASS_DECLARED_on_BLOCKING"
        in out.verdicts["v1"].priority_reasons
    )


def test_gate_output_contains_three_lists() -> None:
    v_ok = VendorGateInput(
        vendor_id="a", has_exploitable_documents=True, signal_hits=_all_hits()
    )
    v_pend = VendorGateInput(
        vendor_id="b",
        has_exploitable_documents=True,
        signal_hits={k: v for k, v in _all_hits().items() if k != "sci_q5_4"},
    )
    v_fail = VendorGateInput(vendor_id="c", has_exploitable_documents=False)
    out = run_eligibility_gate("ws", "lot1", {"a": v_ok, "b": v_pend, "c": v_fail})
    assert isinstance(out.eligible_vendor_ids, list)
    assert isinstance(out.excluded_vendor_ids, list)
    assert isinstance(out.pending_vendor_ids, list)
    assert set(out.eligible_vendor_ids) & set(out.pending_vendor_ids) == set()
    assert set(out.eligible_vendor_ids) & set(out.excluded_vendor_ids) == set()


def test_pipeline_error_when_no_eligible_vendor() -> None:
    v = VendorGateInput(vendor_id="c", has_exploitable_documents=False)
    out = run_eligibility_gate("ws", "lot1", {"c": v})
    with pytest.raises(PipelineError, match="EligibilityGate"):
        require_eligible_vendors_or_raise(out)


def test_null_scores_for_excluded_vendors() -> None:
    v = VendorGateInput(vendor_id="c", has_exploitable_documents=False)
    out = run_eligibility_gate("ws", "lot1", {"c": v})
    row = null_scores_for_ineligible(out.verdicts["c"])
    assert row["score_technique"] is None
    assert row["rang"] == "EXC"


def test_decision_trace_created_for_auto_detection() -> None:
    v = VendorGateInput(
        vendor_id="v1", has_exploitable_documents=True, signal_hits=_all_hits()
    )
    det = evaluate_vendor(v, standard_sci_essential_criteria())
    r = det.criterion_results["sci_q1"]
    assert r.decision_trace_id is not None
    assert r.decision_trace_id in det.traces_by_id


def test_override_requires_justification() -> None:
    crits = [
        EssentialCriterion(
            criterion_id="x1",
            question_number="T1",
            label="t",
            criterion_type="POLICY",
            is_parent=False,
            parent_id=None,
            evidence_expected=["need_x"],
            auto_checkable=True,
            verification_source="DOCUMENT_EVIDENCE",
            gate_severity="BLOCKING",
        )
    ]
    v = VendorGateInput(
        vendor_id="v1",
        has_exploitable_documents=True,
        committee_overrides={
            "x1": ("u1", "   ", datetime.now(tz=UTC)),
        },
    )
    with pytest.raises(ValueError, match="override_justification"):
        evaluate_vendor(v, crits)


def test_contradiction_flagged_when_declared_but_no_doc() -> None:
    crits = [
        EssentialCriterion(
            criterion_id="x1",
            question_number="T1",
            label="t",
            criterion_type="LEGAL",
            is_parent=False,
            parent_id=None,
            evidence_expected=["need_x"],
            auto_checkable=True,
            verification_source="DOCUMENT_EVIDENCE",
            gate_severity="BLOCKING",
        )
    ]
    v = VendorGateInput(
        vendor_id="v1",
        has_exploitable_documents=True,
        signal_hits={"x1": []},
        declared_without_proof_by_criterion={"x1": True},
    )
    det = evaluate_vendor(v, crits)
    tid = det.criterion_results["x1"].decision_trace_id
    assert tid is not None
    assert "declared_but_no_document" in det.traces_by_id[tid].contradictions
