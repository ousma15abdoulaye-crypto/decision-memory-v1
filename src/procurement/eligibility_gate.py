"""
P3.1 — EligibilityGate intelligent (pré-M14, pré-scoring).

Brique additive : aucune intégration ``pipeline_v5_service`` dans ce mandat.
Les décisions s’appuient sur ``criterion_type``, ``gate_severity``,
``verification_source`` et les preuves fournies — pas sur ``question_number`` seul.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from src.procurement.eligibility_models import (
    EligibilityReviewPriority,
    EligibilityVerdict,
    EssentialCriterion,
    EssentialCriterionResult,
    GateDecisionTrace,
    GateOutput,
    VendorEligibilityDetail,
    VendorGateInput,
)

# --- Confiance centralisée (mandat §5.1) : grille DMS {0.6, 0.8, 1.0}
CONFIDENCE_AUTO_DOCUMENTED: float = 0.8
CONFIDENCE_AUTO_UNCERTAIN: float = 0.6
CONFIDENCE_DECLARATION_ONLY: float = 0.6
CONFIDENCE_OVERRIDE_CONFIRMED: float = 1.0

NON_SCORABLE_GATE_B_STATUSES: frozenset[str] = frozenset(
    {"INTERNAL", "REFERENCE", "UNUSABLE"}
)

RESULT_INTERNAL_PASS_CONFIRMED = "PASS_CONFIRMED"
RESULT_INTERNAL_PASS_DECLARED = "PASS_DECLARED"
RESULT_INTERNAL_FAIL_CONFIRMED = "FAIL_CONFIRMED"
RESULT_INTERNAL_PENDING_REVIEW = "PENDING_REVIEW"
RESULT_INTERNAL_NOT_SUBMITTED = "NOT_SUBMITTED"

RESULT_DISPLAY_PASS = "PASS"
RESULT_DISPLAY_FAIL = "FAIL"
RESULT_DISPLAY_PENDING = "PENDING"
RESULT_DISPLAY_NOT_SUBMITTED = "NOT_SUBMITTED"

PROOF_DOCUMENTED = "DOCUMENTED"
PROOF_DECLARATION_ONLY = "DECLARATION_ONLY"
PROOF_VERIFIED_EXTERNALLY = "VERIFIED_EXTERNALLY"

DETECTION_AUTO = "AUTO"
DETECTION_DECLARED_ONLY = "DECLARED_ONLY"
DETECTION_HUMAN_CONFIRMED = "HUMAN_CONFIRMED"

ACTION_NONE = "NONE"
ACTION_REVIEW = "REVIEW"
ACTION_REGULARIZE = "REGULARIZE"
ACTION_EXCLUDE_CONFIRM = "EXCLUDE_CONFIRM"

PRIORITY_BASE = 50


def standard_sci_essential_criteria() -> list[EssentialCriterion]:
    """Catalogue SCI standard (mandat §5.1) — identifiants stables, Qn = traçabilité."""
    rows: list[EssentialCriterion] = [
        EssentialCriterion(
            criterion_id="sci_q1",
            question_number="Q1",
            label="Conditions générales SCI",
            criterion_type="POLICY",
            is_parent=False,
            parent_id=None,
            evidence_expected=["q1_cg"],
            auto_checkable=True,
            verification_source="DOCUMENT_EVIDENCE",
            gate_severity="BLOCKING",
        ),
        EssentialCriterion(
            criterion_id="sci_q2",
            question_number="Q2",
            label="Politiques IAPG (7 politiques)",
            criterion_type="POLICY",
            is_parent=False,
            parent_id=None,
            evidence_expected=["q2_iapg"],
            auto_checkable=True,
            verification_source="DOCUMENT_EVIDENCE",
            gate_severity="BLOCKING",
        ),
        EssentialCriterion(
            criterion_id="sci_q3",
            question_number="Q3",
            label="Non-terrorisme / double usage",
            criterion_type="LEGAL",
            is_parent=False,
            parent_id=None,
            evidence_expected=["q3_dual_use"],
            auto_checkable=True,
            verification_source="DOCUMENT_EVIDENCE",
            gate_severity="BLOCKING",
        ),
        EssentialCriterion(
            criterion_id="sci_q4",
            question_number="Q4",
            label="Sanctions US/UE",
            criterion_type="LEGAL",
            is_parent=False,
            parent_id=None,
            evidence_expected=["q4_sanctions"],
            auto_checkable=True,
            verification_source="DOCUMENT_EVIDENCE",
            gate_severity="BLOCKING",
        ),
        EssentialCriterion(
            criterion_id="sci_q5",
            question_number="Q5",
            label="Qualification légale (agrégat)",
            criterion_type="LEGAL",
            is_parent=True,
            parent_id=None,
            evidence_expected=[],
            auto_checkable=False,
            verification_source="DAO_REQUIREMENT",
            gate_severity="BLOCKING",
        ),
        EssentialCriterion(
            criterion_id="sci_q5_1",
            question_number="Q5.1",
            label="Adresse professionnelle",
            criterion_type="ADMINISTRATIVE",
            is_parent=False,
            parent_id="sci_q5",
            evidence_expected=["q5_addr"],
            auto_checkable=True,
            verification_source="DOCUMENT_EVIDENCE",
            gate_severity="BLOCKING",
        ),
        EssentialCriterion(
            criterion_id="sci_q5_2",
            question_number="Q5.2",
            label="NIF",
            criterion_type="ADMINISTRATIVE",
            is_parent=False,
            parent_id="sci_q5",
            evidence_expected=["q5_nif"],
            auto_checkable=True,
            verification_source="DOCUMENT_EVIDENCE",
            gate_severity="BLOCKING",
        ),
        EssentialCriterion(
            criterion_id="sci_q5_3",
            question_number="Q5.3",
            label="RCCM",
            criterion_type="ADMINISTRATIVE",
            is_parent=False,
            parent_id="sci_q5",
            evidence_expected=["q5_rccm"],
            auto_checkable=True,
            verification_source="DOCUMENT_EVIDENCE",
            gate_severity="BLOCKING",
        ),
        EssentialCriterion(
            criterion_id="sci_q5_4",
            question_number="Q5.4",
            label="Certificat de non-faillite",
            criterion_type="CERTIFICATION",
            is_parent=False,
            parent_id="sci_q5",
            evidence_expected=["q5_non_faillite"],
            auto_checkable=True,
            verification_source="DOCUMENT_EVIDENCE",
            gate_severity="REGULARIZABLE",
        ),
        EssentialCriterion(
            criterion_id="sci_q5_5",
            question_number="Q5.5",
            label="Quitus fiscal",
            criterion_type="CERTIFICATION",
            is_parent=False,
            parent_id="sci_q5",
            evidence_expected=["q5_quitus"],
            auto_checkable=True,
            verification_source="DOCUMENT_EVIDENCE",
            gate_severity="REGULARIZABLE",
        ),
    ]
    return rows


def _new_trace_id() -> str:
    return str(uuid.uuid4())


def _hits_cover_expected(
    expected: list[str], hits: list[str]
) -> tuple[list[str], list[str]]:
    hit_set = set(hits)
    matched: list[str] = []
    missing: list[str] = []
    for token in expected:
        if token in hit_set or any(token in h for h in hits):
            matched.append(token)
        else:
            missing.append(token)
    return matched, missing


def _validate_override(justification: str | None) -> None:
    if justification is None or not str(justification).strip():
        raise ValueError("committee_override requires non-empty override_justification")


def _evaluate_leaf(
    crit: EssentialCriterion,
    vendor: VendorGateInput,
    *,
    force_not_submitted: bool,
    bundle_blocked: bool,
) -> tuple[EssentialCriterionResult, GateDecisionTrace]:
    trace_id = _new_trace_id()
    inputs_used = list(vendor.signal_hits.get(crit.criterion_id, []))
    contradictions: list[str] = []
    matched: list[str] = []
    missing: list[str] = []

    if bundle_blocked:
        rule = "gate_b_bundle_non_scorable"
        res = EssentialCriterionResult(
            criterion_id=crit.criterion_id,
            vendor_id=vendor.vendor_id,
            result_internal=RESULT_INTERNAL_FAIL_CONFIRMED,
            result_display=RESULT_DISPLAY_FAIL,
            proof_level=PROOF_VERIFIED_EXTERNALLY,
            evidence_found=[],
            evidence_label=None,
            detection_method=DETECTION_AUTO,
            confidence=1.0,
            recommended_action=ACTION_EXCLUDE_CONFIRM,
            decision_trace_id=trace_id,
            fail_reason="Bundle Gate B INTERNAL/REFERENCE/UNUSABLE",
            fail_type="POLICY_NON_ACCEPTED",
            committee_override=False,
            override_user_id=None,
            override_at=None,
            override_justification=None,
            locked=False,
        )
        trace = GateDecisionTrace(
            trace_id=trace_id,
            criterion_id=crit.criterion_id,
            vendor_id=vendor.vendor_id,
            inputs_used=inputs_used,
            matched_signals=[],
            missing_signals=["bundle_not_scorable"],
            contradictions=[],
            decision_rule=rule,
            decision_result=RESULT_INTERNAL_FAIL_CONFIRMED,
            confidence=1.0,
        )
        return res, trace

    if force_not_submitted:
        rule = "no_exploitable_documents_all_not_submitted"
        res = EssentialCriterionResult(
            criterion_id=crit.criterion_id,
            vendor_id=vendor.vendor_id,
            result_internal=RESULT_INTERNAL_NOT_SUBMITTED,
            result_display=RESULT_DISPLAY_NOT_SUBMITTED,
            proof_level=PROOF_DECLARATION_ONLY,
            evidence_found=[],
            evidence_label=None,
            detection_method=DETECTION_AUTO,
            confidence=None,
            recommended_action=ACTION_EXCLUDE_CONFIRM,
            decision_trace_id=trace_id,
            fail_reason="Aucun document exploitable",
            fail_type="NOT_SUBMITTED",
            committee_override=False,
            override_user_id=None,
            override_at=None,
            override_justification=None,
            locked=False,
        )
        trace = GateDecisionTrace(
            trace_id=trace_id,
            criterion_id=crit.criterion_id,
            vendor_id=vendor.vendor_id,
            inputs_used=[],
            matched_signals=[],
            missing_signals=["no_submission"],
            contradictions=[],
            decision_rule=rule,
            decision_result=RESULT_INTERNAL_NOT_SUBMITTED,
            confidence=None,
        )
        return res, trace

    ovr = vendor.committee_overrides.get(crit.criterion_id)
    if ovr is not None:
        uid, just, at = ovr
        _validate_override(just)

    res: EssentialCriterionResult
    trace: GateDecisionTrace

    if crit.verification_source == "VENDOR_DECLARATION":
        accepted = bool(vendor.vendor_declaration_acceptance.get(crit.criterion_id))
        if accepted:
            rule = "vendor_declaration_accepted"
            res = EssentialCriterionResult(
                criterion_id=crit.criterion_id,
                vendor_id=vendor.vendor_id,
                result_internal=RESULT_INTERNAL_PASS_DECLARED,
                result_display=RESULT_DISPLAY_PASS,
                proof_level=PROOF_DECLARATION_ONLY,
                evidence_found=list(inputs_used),
                evidence_label=None,
                detection_method=DETECTION_DECLARED_ONLY,
                confidence=CONFIDENCE_DECLARATION_ONLY,
                recommended_action=ACTION_NONE,
                decision_trace_id=trace_id,
                fail_reason=None,
                fail_type=None,
                committee_override=False,
                override_user_id=None,
                override_at=None,
                override_justification=None,
                locked=False,
            )
            trace = GateDecisionTrace(
                trace_id=trace_id,
                criterion_id=crit.criterion_id,
                vendor_id=vendor.vendor_id,
                inputs_used=inputs_used,
                matched_signals=["declaration_accepted"],
                missing_signals=[],
                contradictions=[],
                decision_rule=rule,
                decision_result=RESULT_INTERNAL_PASS_DECLARED,
                confidence=CONFIDENCE_DECLARATION_ONLY,
            )
        else:
            rule = "vendor_declaration_missing"
            res = EssentialCriterionResult(
                criterion_id=crit.criterion_id,
                vendor_id=vendor.vendor_id,
                result_internal=RESULT_INTERNAL_FAIL_CONFIRMED,
                result_display=RESULT_DISPLAY_FAIL,
                proof_level=PROOF_DECLARATION_ONLY,
                evidence_found=[],
                evidence_label=None,
                detection_method=DETECTION_DECLARED_ONLY,
                confidence=CONFIDENCE_DECLARATION_ONLY,
                recommended_action=ACTION_REVIEW,
                decision_trace_id=trace_id,
                fail_reason="Déclaration attendue absente",
                fail_type="POLICY_NON_ACCEPTED",
                committee_override=False,
                override_user_id=None,
                override_at=None,
                override_justification=None,
                locked=False,
            )
            trace = GateDecisionTrace(
                trace_id=trace_id,
                criterion_id=crit.criterion_id,
                vendor_id=vendor.vendor_id,
                inputs_used=inputs_used,
                matched_signals=[],
                missing_signals=["declaration_not_accepted"],
                contradictions=[],
                decision_rule=rule,
                decision_result=RESULT_INTERNAL_FAIL_CONFIRMED,
                confidence=CONFIDENCE_DECLARATION_ONLY,
            )
    else:
        matched, missing = _hits_cover_expected(crit.evidence_expected, inputs_used)
        declared_nop = bool(
            vendor.declared_without_proof_by_criterion.get(crit.criterion_id)
        )
        if declared_nop and missing:
            contradictions.append("declared_but_no_document")
        if missing:
            if crit.gate_severity == "REGULARIZABLE":
                rule = "presence_required_regularizable"
                internal = RESULT_INTERNAL_PENDING_REVIEW
                display = RESULT_DISPLAY_PENDING
                fail_t = "REGULARIZATION_REQUIRED"
                action = ACTION_REGULARIZE
                conf = CONFIDENCE_AUTO_DOCUMENTED
            else:
                rule = "presence_required_blocking"
                internal = RESULT_INTERNAL_FAIL_CONFIRMED
                display = RESULT_DISPLAY_FAIL
                fail_t = "MISSING_LEGAL_DOC"
                action = ACTION_EXCLUDE_CONFIRM
                conf = (
                    CONFIDENCE_AUTO_UNCERTAIN
                    if declared_nop
                    else CONFIDENCE_AUTO_DOCUMENTED
                )
            res = EssentialCriterionResult(
                criterion_id=crit.criterion_id,
                vendor_id=vendor.vendor_id,
                result_internal=internal,
                result_display=display,
                proof_level=(
                    PROOF_DECLARATION_ONLY if declared_nop else PROOF_DOCUMENTED
                ),
                evidence_found=matched,
                evidence_label=crit.label if matched else None,
                detection_method=DETECTION_AUTO,
                confidence=conf,
                recommended_action=action,
                decision_trace_id=trace_id,
                fail_reason="Pièce attendue absente ou incomplète",
                fail_type=fail_t,
                committee_override=False,
                override_user_id=None,
                override_at=None,
                override_justification=None,
                locked=False,
            )
            trace = GateDecisionTrace(
                trace_id=trace_id,
                criterion_id=crit.criterion_id,
                vendor_id=vendor.vendor_id,
                inputs_used=inputs_used,
                matched_signals=matched,
                missing_signals=missing,
                contradictions=contradictions,
                decision_rule=rule,
                decision_result=res.result_internal,
                confidence=res.confidence,
            )
        else:
            rule = "presence_required_all_expected_signals"
            res = EssentialCriterionResult(
                criterion_id=crit.criterion_id,
                vendor_id=vendor.vendor_id,
                result_internal=RESULT_INTERNAL_PASS_CONFIRMED,
                result_display=RESULT_DISPLAY_PASS,
                proof_level=PROOF_DOCUMENTED,
                evidence_found=matched,
                evidence_label=crit.label,
                detection_method=DETECTION_AUTO,
                confidence=CONFIDENCE_AUTO_DOCUMENTED,
                recommended_action=ACTION_NONE,
                decision_trace_id=trace_id,
                fail_reason=None,
                fail_type=None,
                committee_override=False,
                override_user_id=None,
                override_at=None,
                override_justification=None,
                locked=False,
            )
            trace = GateDecisionTrace(
                trace_id=trace_id,
                criterion_id=crit.criterion_id,
                vendor_id=vendor.vendor_id,
                inputs_used=inputs_used,
                matched_signals=matched,
                missing_signals=missing,
                contradictions=contradictions,
                decision_rule=rule,
                decision_result=res.result_internal,
                confidence=res.confidence,
            )

    if ovr is not None:
        uid, just, at = ovr
        prev_res = res
        prev_trace = trace
        if prev_res.result_internal == RESULT_INTERNAL_FAIL_CONFIRMED:
            res = EssentialCriterionResult(
                criterion_id=crit.criterion_id,
                vendor_id=vendor.vendor_id,
                result_internal=RESULT_INTERNAL_PASS_CONFIRMED,
                result_display=RESULT_DISPLAY_PASS,
                proof_level=prev_res.proof_level,
                evidence_found=list(prev_res.evidence_found),
                evidence_label=prev_res.evidence_label,
                detection_method=DETECTION_HUMAN_CONFIRMED,
                confidence=CONFIDENCE_OVERRIDE_CONFIRMED,
                recommended_action=ACTION_REVIEW,
                decision_trace_id=trace_id,
                fail_reason=None,
                fail_type=None,
                committee_override=True,
                override_user_id=uid,
                override_at=at,
                override_justification=just,
                locked=True,
            )
            extra_contra: list[str] = list(prev_trace.contradictions)
            if crit.gate_severity == "BLOCKING":
                extra_contra.append("blocking_fail_overridden_to_pass")
            trace = GateDecisionTrace(
                trace_id=trace_id,
                criterion_id=crit.criterion_id,
                vendor_id=vendor.vendor_id,
                inputs_used=inputs_used,
                matched_signals=list(prev_trace.matched_signals),
                missing_signals=list(prev_trace.missing_signals),
                contradictions=extra_contra,
                decision_rule=prev_trace.decision_rule
                + "+committee_override_fail_to_pass",
                decision_result=RESULT_INTERNAL_PASS_CONFIRMED,
                confidence=CONFIDENCE_OVERRIDE_CONFIRMED,
            )

    return res, trace


def _aggregate_q5(
    children: list[EssentialCriterion],
    by_id: dict[str, EssentialCriterionResult],
    vendor_id: str,
) -> tuple[EssentialCriterionResult, GateDecisionTrace]:
    trace_id = _new_trace_id()
    ch_res = [by_id[c.criterion_id] for c in children]
    if ch_res and all(
        r.result_internal == RESULT_INTERNAL_NOT_SUBMITTED for r in ch_res
    ):
        trace = GateDecisionTrace(
            trace_id=trace_id,
            criterion_id="sci_q5",
            vendor_id=vendor_id,
            inputs_used=[r.criterion_id for r in ch_res],
            matched_signals=[],
            missing_signals=["all_children_not_submitted"],
            contradictions=[],
            decision_rule="q5_aggregate_all_not_submitted",
            decision_result=RESULT_INTERNAL_NOT_SUBMITTED,
            confidence=None,
        )
        res = EssentialCriterionResult(
            criterion_id="sci_q5",
            vendor_id=vendor_id,
            result_internal=RESULT_INTERNAL_NOT_SUBMITTED,
            result_display=RESULT_DISPLAY_NOT_SUBMITTED,
            proof_level=PROOF_DECLARATION_ONLY,
            evidence_found=[],
            evidence_label=None,
            detection_method=DETECTION_AUTO,
            confidence=None,
            recommended_action=ACTION_EXCLUDE_CONFIRM,
            decision_trace_id=trace_id,
            fail_reason="Aucune pièce Q5 exploitable",
            fail_type="NOT_SUBMITTED",
            committee_override=False,
            override_user_id=None,
            override_at=None,
            override_justification=None,
            locked=False,
        )
        return res, trace

    blocking_fail = any(
        by_id[c.criterion_id].result_internal == RESULT_INTERNAL_FAIL_CONFIRMED
        for c in children
        if c.gate_severity == "BLOCKING"
    )
    blocking_pending = any(
        by_id[c.criterion_id].result_internal == RESULT_INTERNAL_PENDING_REVIEW
        for c in children
        if c.gate_severity == "BLOCKING"
    )
    only_reg_fail = (
        not blocking_fail
        and not blocking_pending
        and any(
            by_id[c.criterion_id].result_internal
            in (RESULT_INTERNAL_FAIL_CONFIRMED, RESULT_INTERNAL_PENDING_REVIEW)
            for c in children
            if c.gate_severity == "REGULARIZABLE"
        )
    )
    decl_children = [c for c in children if c.gate_severity == "DECLARATIVE"]
    non_decl_children = [c for c in children if c.gate_severity != "DECLARATIVE"]
    only_decl_missing = (
        not blocking_fail
        and not blocking_pending
        and bool(decl_children)
        and all(
            by_id[c.criterion_id].result_internal == RESULT_INTERNAL_PASS_DECLARED
            for c in decl_children
        )
        and (
            not non_decl_children
            or all(
                by_id[c.criterion_id].result_internal == RESULT_INTERNAL_PASS_CONFIRMED
                for c in non_decl_children
            )
        )
    )

    if blocking_fail:
        internal = RESULT_INTERNAL_FAIL_CONFIRMED
        display = RESULT_DISPLAY_FAIL
        rule = "q5_aggregate_any_blocking_fail_confirmed"
    elif blocking_pending:
        internal = RESULT_INTERNAL_PENDING_REVIEW
        display = RESULT_DISPLAY_PENDING
        rule = "q5_aggregate_blocking_pending"
    elif only_reg_fail:
        internal = RESULT_INTERNAL_PENDING_REVIEW
        display = RESULT_DISPLAY_PENDING
        rule = "q5_aggregate_only_regularizable_fail"
    elif only_decl_missing:
        internal = RESULT_INTERNAL_PASS_DECLARED
        display = RESULT_DISPLAY_PASS
        rule = "q5_aggregate_only_declarative_missing"
    elif all(r.result_internal == RESULT_INTERNAL_PASS_CONFIRMED for r in ch_res):
        internal = RESULT_INTERNAL_PASS_CONFIRMED
        display = RESULT_DISPLAY_PASS
        rule = "q5_aggregate_all_confirmed"
    elif all(
        r.result_internal
        in (RESULT_INTERNAL_PASS_CONFIRMED, RESULT_INTERNAL_PASS_DECLARED)
        for r in ch_res
    ):
        internal = RESULT_INTERNAL_PASS_DECLARED
        display = RESULT_DISPLAY_PASS
        rule = "q5_aggregate_mixed_confirmed_declared"
    else:
        internal = RESULT_INTERNAL_PENDING_REVIEW
        display = RESULT_DISPLAY_PENDING
        rule = "q5_aggregate_default_pending"

    fail_reason = (
        None
        if internal != RESULT_INTERNAL_FAIL_CONFIRMED
        else "Sous-critère bloquant en échec"
    )
    trace = GateDecisionTrace(
        trace_id=trace_id,
        criterion_id="sci_q5",
        vendor_id=vendor_id,
        inputs_used=[r.criterion_id for r in ch_res],
        matched_signals=[r.result_internal for r in ch_res],
        missing_signals=[],
        contradictions=[],
        decision_rule=rule,
        decision_result=internal,
        confidence=CONFIDENCE_AUTO_DOCUMENTED,
    )
    proof = (
        PROOF_DOCUMENTED
        if internal == RESULT_INTERNAL_PASS_CONFIRMED
        else PROOF_DECLARATION_ONLY
    )
    res = EssentialCriterionResult(
        criterion_id="sci_q5",
        vendor_id=vendor_id,
        result_internal=internal,
        result_display=display,
        proof_level=proof,
        evidence_found=[r.criterion_id for r in ch_res],
        evidence_label="Q5 agrégat",
        detection_method=DETECTION_AUTO,
        confidence=CONFIDENCE_AUTO_DOCUMENTED,
        recommended_action=(
            ACTION_REVIEW if internal != RESULT_INTERNAL_PASS_CONFIRMED else ACTION_NONE
        ),
        decision_trace_id=trace_id,
        fail_reason=fail_reason,
        fail_type=(
            "MISSING_LEGAL_DOC" if internal == RESULT_INTERNAL_FAIL_CONFIRMED else None
        ),
        committee_override=False,
        override_user_id=None,
        override_at=None,
        override_justification=None,
        locked=False,
    )
    return res, trace


def _blocking_leaf_ids(criteria: Sequence[EssentialCriterion]) -> list[str]:
    return [
        c.criterion_id
        for c in criteria
        if (not c.is_parent) and c.gate_severity == "BLOCKING"
    ]


def _documentary_strength(
    blocking_ids: Sequence[str],
    by_id: dict[str, EssentialCriterionResult],
) -> str:
    if not blocking_ids:
        return "LOW"
    documented = 0
    declared_only = 0
    for cid in blocking_ids:
        r = by_id.get(cid)
        if not r:
            continue
        if (
            r.result_internal == RESULT_INTERNAL_PASS_CONFIRMED
            and r.proof_level == PROOF_DOCUMENTED
        ):
            documented += 1
        elif r.result_internal in (
            RESULT_INTERNAL_PASS_DECLARED,
            RESULT_INTERNAL_PASS_CONFIRMED,
        ):
            if r.proof_level == PROOF_DECLARATION_ONLY:
                declared_only += 1
            elif r.proof_level == PROOF_DOCUMENTED:
                documented += 1
        elif r.result_internal in (
            RESULT_INTERNAL_FAIL_CONFIRMED,
            RESULT_INTERNAL_PENDING_REVIEW,
            RESULT_INTERNAL_NOT_SUBMITTED,
        ):
            declared_only += 1
    total = len(blocking_ids)
    ratio_block = documented / total if total else 0.0
    majority_doc = documented > declared_only
    if ratio_block >= 0.9 and majority_doc:
        return "HIGH"
    if ratio_block >= 0.7 or (documented > 0 and declared_only > 0):
        return "MEDIUM"
    if ratio_block < 0.7 or declared_only >= documented:
        return "LOW"
    return "MEDIUM"


def _compute_coverage(
    by_id: dict[str, EssentialCriterionResult],
    leaves: Sequence[str],
    blocking_leaf_ids: Sequence[str],
) -> tuple[int, int, int, float, float]:
    auto_v = 0
    human_v = 0
    total = len(leaves)
    for cid in leaves:
        r = by_id[cid]
        if r.detection_method == DETECTION_AUTO and r.result_internal in (
            RESULT_INTERNAL_PASS_CONFIRMED,
            RESULT_INTERNAL_PASS_DECLARED,
        ):
            auto_v += 1
        if r.detection_method == DETECTION_HUMAN_CONFIRMED:
            human_v += 1
    verified = sum(
        1
        for cid in leaves
        if by_id[cid].result_internal
        in (RESULT_INTERNAL_PASS_CONFIRMED, RESULT_INTERNAL_PASS_DECLARED)
    )
    vratio = verified / total if total else 0.0
    documented_blocking = sum(
        1
        for cid in blocking_leaf_ids
        if by_id.get(cid)
        and by_id[cid].result_internal == RESULT_INTERNAL_PASS_CONFIRMED
        and by_id[cid].proof_level == PROOF_DOCUMENTED
    )
    btot = len(blocking_leaf_ids)
    bratio = documented_blocking / btot if btot else 0.0
    return auto_v, human_v, total, vratio, bratio


def _priority_tier(score: int) -> str:
    if score >= 85:
        return "URGENT"
    if score >= 65:
        return "HIGH"
    if score >= 40:
        return "NORMAL"
    return "LOW"


def _priority_score_for_vendor(
    verdict: EligibilityVerdict,
    vendor: VendorGateInput,
    by_id: dict[str, EssentialCriterionResult],
    traces: dict[str, GateDecisionTrace],
    criterion_by_id: dict[str, EssentialCriterion],
) -> tuple[int, list[str]]:
    score = PRIORITY_BASE
    reasons: list[str] = []
    if verdict.gate_result == RESULT_DISPLAY_FAIL:
        for cid in verdict.failing_criteria:
            r = by_id.get(cid)
            if (
                r
                and r.result_internal == RESULT_INTERNAL_FAIL_CONFIRMED
                and r.confidence is not None
                and r.confidence < 0.75
            ):
                score += 30
                reasons.append("exclusion_BLOCKING_confidence_lt_0_75")
                break
    if (
        verdict.documentary_strength == "LOW"
        and verdict.gate_result == RESULT_DISPLAY_PASS
        and verdict.eligible
    ) or (
        verdict.documentary_strength == "LOW"
        and verdict.gate_result == RESULT_DISPLAY_PENDING
    ):
        score += 25
        reasons.append("pass_or_pending_weak_documentary_strength_LOW")
    if vendor.is_important_vendor:
        for r in by_id.values():
            crit_def = criterion_by_id.get(r.criterion_id)
            if (
                r.criterion_id != "sci_q5"
                and crit_def is not None
                and crit_def.gate_severity == "BLOCKING"
                and r.result_internal == RESULT_INTERNAL_PASS_DECLARED
                and r.detection_method == DETECTION_DECLARED_ONLY
            ):
                score += 20
                reasons.append("important_vendor_PASS_DECLARED_on_BLOCKING")
                break
    for tr in traces.values():
        if tr.contradictions:
            score += 15
            reasons.append("contradiction_detected")
            break
    for r in by_id.values():
        if r.fail_type == "REGULARIZATION_REQUIRED":
            score += 10
            reasons.append("regularizable_failure")
            break
    if verdict.pending_criteria:
        score += 5
        reasons.append("pending_criteria_non_empty")
    score = max(0, min(100, score))
    return score, reasons


def evaluate_vendor(
    vendor: VendorGateInput,
    criteria: Sequence[EssentialCriterion],
) -> VendorEligibilityDetail:
    leaves = [c for c in criteria if not c.is_parent]
    q5_children = [c for c in leaves if c.parent_id == "sci_q5"]
    other_leaves = [c for c in leaves if c.parent_id != "sci_q5"]
    traces: dict[str, GateDecisionTrace] = {}
    bstat_eval = (vendor.bundle_gate_b_status or "").strip().upper()
    bundle_blocked = bstat_eval in NON_SCORABLE_GATE_B_STATUSES
    force_ns = not vendor.has_exploitable_documents
    results: dict[str, EssentialCriterionResult] = {}
    for crit in other_leaves:
        res, tr = _evaluate_leaf(
            crit,
            vendor,
            force_not_submitted=force_ns,
            bundle_blocked=bundle_blocked,
        )
        results[crit.criterion_id] = res
        traces[tr.trace_id] = tr
    for crit in q5_children:
        res, tr = _evaluate_leaf(
            crit,
            vendor,
            force_not_submitted=force_ns,
            bundle_blocked=bundle_blocked,
        )
        results[crit.criterion_id] = res
        traces[tr.trace_id] = tr
    q5_internal: str | None = None
    q5_display: str | None = None
    if q5_children:
        agg, agg_tr = _aggregate_q5(q5_children, results, vendor.vendor_id)
        results["sci_q5"] = agg
        traces[agg_tr.trace_id] = agg_tr
        q5_internal = agg.result_internal
        q5_display = agg.result_display
    return VendorEligibilityDetail(
        vendor_id=vendor.vendor_id,
        criterion_results=results,
        traces_by_id=traces,
        q5_aggregate_internal=q5_internal,
        q5_aggregate_display=q5_display,
    )


def _verdict_from_detail(
    vendor: VendorGateInput,
    detail: VendorEligibilityDetail,
    criteria: Sequence[EssentialCriterion],
) -> EligibilityVerdict:
    by_cid = {c.criterion_id: c for c in criteria}
    leaves = [c.criterion_id for c in criteria if not c.is_parent]
    has_q5_aggregate = "sci_q5" in detail.criterion_results
    leaves_plus = [*leaves, "sci_q5"] if has_q5_aggregate else list(leaves)
    blocking_ids = _blocking_leaf_ids(criteria)
    auto_v, human_v, total, vratio, bratio = _compute_coverage(
        detail.criterion_results, leaves, blocking_ids
    )
    doc_strength = _documentary_strength(blocking_ids, detail.criterion_results)

    blocking_fail = any(
        detail.criterion_results[cid].result_internal == RESULT_INTERNAL_FAIL_CONFIRMED
        for cid in blocking_ids
        if cid in detail.criterion_results
    ) or (
        has_q5_aggregate
        and detail.criterion_results.get("sci_q5") is not None
        and detail.criterion_results["sci_q5"].result_internal
        == RESULT_INTERNAL_FAIL_CONFIRMED
    )

    pending_crit = [
        cid
        for cid, r in detail.criterion_results.items()
        if r.result_internal == RESULT_INTERNAL_PENDING_REVIEW
    ]
    failing_crit = [
        cid
        for cid, r in detail.criterion_results.items()
        if r.result_internal == RESULT_INTERNAL_FAIL_CONFIRMED
    ]
    not_submitted_dominant = all(
        detail.criterion_results[cid].result_internal == RESULT_INTERNAL_NOT_SUBMITTED
        for cid in leaves
        if cid in detail.criterion_results
    ) and (
        (not has_q5_aggregate)
        or (
            detail.criterion_results.get("sci_q5") is not None
            and detail.criterion_results["sci_q5"].result_internal
            == RESULT_INTERNAL_NOT_SUBMITTED
        )
    )

    bstat = (vendor.bundle_gate_b_status or "").strip().upper()
    bundle_non_scorable = bstat in NON_SCORABLE_GATE_B_STATUSES

    dominant: str | None
    if not_submitted_dominant:
        dominant = "NOT_SUBMITTED"
        gate_result = RESULT_DISPLAY_FAIL
        eligible = False
    elif bundle_non_scorable:
        dominant = "GATE_B_NON_SCORABLE"
        gate_result = RESULT_DISPLAY_FAIL
        eligible = False
    elif blocking_fail:
        dominant = "BLOCKING_FAIL"
        gate_result = RESULT_DISPLAY_FAIL
        eligible = False
    elif pending_crit or (
        has_q5_aggregate
        and detail.criterion_results.get("sci_q5") is not None
        and detail.criterion_results["sci_q5"].result_internal
        == RESULT_INTERNAL_PENDING_REVIEW
    ):
        dominant = "PENDING_REGULARIZATION_OR_REVIEW"
        gate_result = RESULT_DISPLAY_PENDING
        eligible = False
    elif doc_strength == "LOW":
        dominant = "WEAK_DOCUMENTARY"
        gate_result = RESULT_DISPLAY_PENDING
        eligible = False
    else:
        dominant = None
        gate_result = RESULT_DISPLAY_PASS
        eligible = True

    verdict = EligibilityVerdict(
        vendor_id=vendor.vendor_id,
        eligible=eligible,
        gate_result=gate_result,
        failing_criteria=failing_crit,
        pending_criteria=pending_crit,
        dominant_cause=dominant,
        auto_verified_count=auto_v,
        human_required_count=human_v,
        total_criteria_count=len(leaves_plus),
        verification_coverage_ratio=vratio,
        blocking_verified_ratio=bratio,
        documentary_strength=doc_strength,
        priority_score=0,
        priority_reasons=[],
        locked=False,
    )
    ps, pr = _priority_score_for_vendor(
        verdict,
        vendor,
        detail.criterion_results,
        detail.traces_by_id,
        by_cid,
    )
    if any(
        r.committee_override and r.result_internal == RESULT_INTERNAL_PASS_CONFIRMED
        for r in detail.criterion_results.values()
    ):
        for cid, r in detail.criterion_results.items():
            if (
                r.committee_override
                and by_cid.get(cid)
                and by_cid[cid].gate_severity == "BLOCKING"
                and r.result_internal == RESULT_INTERNAL_PASS_CONFIRMED
            ):
                pr = [*pr, "blocking_fail_to_pass_committee_override"]
                break
    verdict = EligibilityVerdict(
        vendor_id=verdict.vendor_id,
        eligible=verdict.eligible,
        gate_result=verdict.gate_result,
        failing_criteria=verdict.failing_criteria,
        pending_criteria=verdict.pending_criteria,
        dominant_cause=verdict.dominant_cause,
        auto_verified_count=verdict.auto_verified_count,
        human_required_count=verdict.human_required_count,
        total_criteria_count=verdict.total_criteria_count,
        verification_coverage_ratio=verdict.verification_coverage_ratio,
        blocking_verified_ratio=verdict.blocking_verified_ratio,
        documentary_strength=verdict.documentary_strength,
        priority_score=ps,
        priority_reasons=pr,
        locked=verdict.locked,
    )
    return verdict


def run_eligibility_gate(
    workspace_id: str,
    lot_id: str,
    vendors: dict[str, VendorGateInput],
    *,
    criteria: Sequence[EssentialCriterion] | None = None,
    evaluated_at: datetime | None = None,
) -> GateOutput:
    crit_list = (
        list(criteria) if criteria is not None else standard_sci_essential_criteria()
    )
    evaluated_at = evaluated_at or datetime.now(tz=UTC)
    verdicts: dict[str, EligibilityVerdict] = {}

    for vid, v in vendors.items():
        det = evaluate_vendor(v, crit_list)
        verdicts[vid] = _verdict_from_detail(v, det, crit_list)

    eligible = [
        vid
        for vid, ver in verdicts.items()
        if ver.eligible and ver.gate_result == RESULT_DISPLAY_PASS
    ]
    excluded = [
        vid for vid, ver in verdicts.items() if ver.gate_result == RESULT_DISPLAY_FAIL
    ]
    pending = [
        vid
        for vid, ver in verdicts.items()
        if ver.gate_result == RESULT_DISPLAY_PENDING
    ]
    not_submitted_n = sum(
        1 for ver in verdicts.values() if ver.dominant_cause == "NOT_SUBMITTED"
    )

    review: list[EligibilityReviewPriority] = []
    for vid, ver in verdicts.items():
        vinp = vendors[vid]
        review.append(
            EligibilityReviewPriority(
                vendor_id=vid,
                vendor_name=vinp.vendor_name or vid,
                priority_score=ver.priority_score,
                priority_tier=_priority_tier(ver.priority_score),
                reasons=list(ver.priority_reasons),
            )
        )
    review.sort(key=lambda x: x.priority_score, reverse=True)

    return GateOutput(
        workspace_id=workspace_id,
        lot_id=lot_id,
        evaluated_at=evaluated_at,
        eligible_vendor_ids=eligible,
        excluded_vendor_ids=excluded,
        pending_vendor_ids=pending,
        verdicts=verdicts,
        review_queue=review,
        total_submitted=len(vendors),
        total_eligible=len(eligible),
        total_excluded=len(excluded),
        total_pending=len(pending),
        total_not_submitted=not_submitted_n,
    )


def require_eligible_vendors_or_raise(gate_output: GateOutput) -> None:
    """Règle dure mandat §8 — utilise ``PipelineError`` du pipeline existant."""
    if not gate_output.eligible_vendor_ids:
        from src.services.pipeline_v5_service import PipelineError

        raise PipelineError(
            "EligibilityGate: aucun vendor éligible — scoring impossible"
        )


def null_scores_for_ineligible(verdict: EligibilityVerdict) -> dict[str, object]:
    """Règle anti-#DIV/0! mandat §9 pour vendeurs non éligibles au scoring.

    Ne doit être appelée que pour un verdict non éligible (évite d'écraser
    silencieusement des scores pour un fournisseur autorisé au scoring).
    """
    if verdict.eligible:
        raise ValueError(
            "null_scores_for_ineligible() must not be called for an eligible vendor"
        )
    return {
        "score_technique": None,
        "score_commercial": None,
        "score_durabilité": None,
        "total": None,
        "rang": "EXC",
    }
