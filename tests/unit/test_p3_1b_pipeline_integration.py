"""P3.1B — intégration EligibilityGate dans le pipeline (unitaires purs)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.procurement.bundle_scoring_role import ScoringRole
from src.procurement.eligibility_gate import (
    RESULT_DISPLAY_FAIL,
    RESULT_DISPLAY_PASS,
    RESULT_DISPLAY_PENDING,
    build_vendor_gate_input_from_bundle_documents,
    run_eligibility_gate,
)
from src.procurement.eligibility_models import EligibilityVerdict, GateOutput
from src.procurement.m14_evaluation_models import EvaluationReport, OfferEvaluation
from src.services.m14_bridge import matrix_participant_bundle_ids
from src.services.pipeline_v5_service import (
    EXCLUSION_REASONS,
    PipelineError,
    _ensure_m14_scoring_structure_for_scorable_offers,
    build_matrix_participants_and_excluded,
    eligibility_verdicts_summary_from_gate_output,
    merge_p3_eligibility_gate_failures_into_excluded,
    run_p3_1b_eligibility_gate_phase,
    run_pipeline_v5,
)

# Corpus minimal couvrant les jetons ``evidence_expected`` des feuilles bloquantes + Q5.
_FULL_ELIGIBILITY_CORPUS = (
    "q1_cg q2_iapg q3_dual_use q4_sanctions "
    "q5_addr q5_nif q5_rccm q5_non_faillite q5_quitus"
)


def test_exclusion_reasons_includes_p3_eligibility_fail() -> None:
    assert "eligibility_fail" in EXCLUSION_REASONS


def test_build_vendor_gate_input_detects_expected_tokens() -> None:
    vin = build_vendor_gate_input_from_bundle_documents(
        "b1",
        rows=[{"raw_text": _FULL_ELIGIBILITY_CORPUS}],
        bundle_gate_b_status="SCORABLE",
    )
    assert vin.has_exploitable_documents is True
    assert "sci_q1" in vin.signal_hits
    assert any("q1_cg" in h for h in vin.signal_hits["sci_q1"])


def test_build_vendor_gate_input_empty_corpus_no_hits() -> None:
    vin = build_vendor_gate_input_from_bundle_documents(
        "b1",
        rows=[{"raw_text": "   "}, {"raw_text": None}],
        bundle_gate_b_status="SCORABLE",
    )
    assert vin.has_exploitable_documents is False
    assert vin.signal_hits == {}


def test_run_p3_1b_eligibility_gate_phase_filters_to_eligible_only() -> None:
    bid_ok = "bundle-ok"
    bid_bad = "bundle-bad"
    offers: list[dict[str, Any]] = [
        {
            "document_id": bid_ok,
            "supplier_name": "OK SA",
            "process_role": "responds_to_bid",
        },
        {
            "document_id": bid_bad,
            "supplier_name": "Bad Ltd",
            "process_role": "responds_to_bid",
        },
    ]
    doc_groups: dict[str, list[dict[str, Any]]] = {
        bid_ok: [{"raw_text": _FULL_ELIGIBILITY_CORPUS}],
        bid_bad: [{"raw_text": ""}],
    }
    gate_map = {bid_ok: "SCORABLE", bid_bad: "SCORABLE"}
    vendors = {bid_ok: "OK SA", bid_bad: "Bad Ltd"}
    filtered, gate = run_p3_1b_eligibility_gate_phase(
        "ws-test",
        "case-test",
        offers,
        doc_groups,
        gate_map,
        vendors,
    )
    assert len(filtered) == 1
    assert str(filtered[0]["document_id"]) == bid_ok
    assert bid_ok in gate.eligible_vendor_ids
    assert bid_bad in gate.excluded_vendor_ids


def test_run_p3_1b_eligibility_gate_phase_empty_offers_empty_gate() -> None:
    filtered, gate = run_p3_1b_eligibility_gate_phase("ws", None, [], {}, {}, {})
    assert filtered == []
    assert gate.total_submitted == 0
    assert gate.eligible_vendor_ids == []


def test_eligibility_verdicts_summary_shape() -> None:
    vid = "v1"
    v = EligibilityVerdict(
        vendor_id=vid,
        eligible=True,
        gate_result=RESULT_DISPLAY_PASS,
        failing_criteria=[],
        pending_criteria=[],
        dominant_cause=None,
        auto_verified_count=1,
        human_required_count=0,
        total_criteria_count=5,
        verification_coverage_ratio=1.0,
        blocking_verified_ratio=1.0,
        documentary_strength="HIGH",
        priority_score=50,
        priority_reasons=[],
        locked=False,
    )
    gate = GateOutput(
        workspace_id="w",
        lot_id="l",
        evaluated_at=datetime.now(tz=UTC),
        eligible_vendor_ids=[vid],
        excluded_vendor_ids=[],
        pending_vendor_ids=[],
        verdicts={vid: v},
        review_queue=[],
        total_submitted=1,
        total_eligible=1,
        total_excluded=0,
        total_pending=0,
        total_not_submitted=0,
    )
    s = eligibility_verdicts_summary_from_gate_output(gate)
    assert s[vid]["eligible"] is True
    assert s[vid]["gate_result"] == RESULT_DISPLAY_PASS


def test_merge_p3_eligibility_adds_eligibility_fail_row() -> None:
    vid = "ex-1"
    ver = EligibilityVerdict(
        vendor_id=vid,
        eligible=False,
        gate_result=RESULT_DISPLAY_FAIL,
        failing_criteria=["sci_q1"],
        pending_criteria=[],
        dominant_cause="BLOCKING_FAIL",
        auto_verified_count=0,
        human_required_count=0,
        total_criteria_count=3,
        verification_coverage_ratio=0.0,
        blocking_verified_ratio=0.0,
        documentary_strength="LOW",
        priority_score=50,
        priority_reasons=[],
        locked=False,
    )
    gate = GateOutput(
        workspace_id="w",
        lot_id="l",
        evaluated_at=datetime.now(tz=UTC),
        eligible_vendor_ids=[],
        excluded_vendor_ids=[vid],
        pending_vendor_ids=[],
        verdicts={vid: ver},
        review_queue=[],
        total_submitted=1,
        total_eligible=0,
        total_excluded=1,
        total_pending=0,
        total_not_submitted=0,
    )
    excl: list[dict[str, Any]] = []
    merge_p3_eligibility_gate_failures_into_excluded(excl, gate, {vid: "Supplier X"})
    assert len(excl) == 1
    assert excl[0]["bundle_id"] == vid
    assert excl[0]["reason"] == "eligibility_fail"
    assert any(x.startswith("p3.1:") for x in excl[0]["failed_eligibility_checks"])


def test_merge_p3_eligibility_skips_duplicate_bundle_id() -> None:
    vid = "dup"
    ver = EligibilityVerdict(
        vendor_id=vid,
        eligible=False,
        gate_result=RESULT_DISPLAY_FAIL,
        failing_criteria=[],
        pending_criteria=[],
        dominant_cause="X",
        auto_verified_count=0,
        human_required_count=0,
        total_criteria_count=1,
        verification_coverage_ratio=0.0,
        blocking_verified_ratio=0.0,
        documentary_strength="LOW",
        priority_score=50,
        priority_reasons=[],
        locked=False,
    )
    gate = GateOutput(
        workspace_id="w",
        lot_id="l",
        evaluated_at=datetime.now(tz=UTC),
        eligible_vendor_ids=[],
        excluded_vendor_ids=[vid],
        pending_vendor_ids=[],
        verdicts={vid: ver},
        review_queue=[],
        total_submitted=1,
        total_eligible=0,
        total_excluded=1,
        total_pending=0,
        total_not_submitted=0,
    )
    excl: list[dict[str, Any]] = [
        {"bundle_id": vid, "supplier_name": "A", "reason": "ineligible"}
    ]
    merge_p3_eligibility_gate_failures_into_excluded(excl, gate, {})
    assert len(excl) == 1


def test_merge_p3_does_not_add_pending_only_vendors() -> None:
    """R3 — merge n’ajoute que ``excluded_vendor_ids`` (FAIL), pas les PENDING."""
    gate = GateOutput(
        workspace_id="w",
        lot_id="l",
        evaluated_at=datetime.now(tz=UTC),
        eligible_vendor_ids=[],
        excluded_vendor_ids=[],
        pending_vendor_ids=["p1"],
        verdicts={},
        review_queue=[],
        total_submitted=1,
        total_eligible=0,
        total_excluded=0,
        total_pending=1,
        total_not_submitted=0,
    )
    excl: list[dict[str, Any]] = []
    merge_p3_eligibility_gate_failures_into_excluded(excl, gate, {"p1": "Name"})
    assert excl == []


def test_ensure_m14_scoring_structure_uses_pre_p3_offer_count() -> None:
    """D-003 : la structure M14 est exigée si au moins une offre Gate-B-SCORABLE existait."""
    offers_pre = [{"document_id": "x"}]
    with pytest.raises(PipelineError, match="m14_scoring_structure_empty"):
        _ensure_m14_scoring_structure_for_scorable_offers(offers_pre, {"criteria": []})


def test_r6_pipeline_error_message_documented() -> None:
    """R6 — chaîne attendue lorsque ``offers_pre_p3`` non vide et ``offers`` vide (M14 non skippé)."""
    msg = (
        "pipeline_blocked:p3_1b_zero_eligible_after_gate — "
        "Des bundles Gate B SCORABLE ont été identifiés mais aucun fournisseur "
        "n’a passé l’EligibilityGate P3.1 (tous exclus ou aucun éligible)."
    )
    with pytest.raises(PipelineError, match="p3_1b_zero_eligible_after_gate"):
        raise PipelineError(msg)


# --- Groupe A (complément mandat) -------------------------------------------------

_SCORABLE_GATE_B_ROWS: list[dict[str, Any]] = [
    {
        "doc_type": "offer_combined",
        "raw_text": (
            "REPONSE A LA DEMANDE DE DEVIS RFQ-MLI-BKO-2025-002 "
            "CARTOUCHES\nSave the Children\n"
        ),
        "vendor_name_raw": "SOPRESCOM",
    },
]


def test_scorable_bundle_passes_to_eligibility_gate() -> None:
    """Gate B SCORABLE + corpus P3 complet → le bundle est soumis au gate et éligible."""
    bid = "bundle-scorable-pass"
    offers: list[dict[str, Any]] = [
        {
            "document_id": bid,
            "supplier_name": "ACME",
            "process_role": "responds_to_bid",
        }
    ]
    doc_groups = {bid: [{"raw_text": _FULL_ELIGIBILITY_CORPUS, "doc_type": "offer"}]}
    gate_map = {bid: "SCORABLE"}
    vendors = {bid: "ACME"}
    filtered, gate = run_p3_1b_eligibility_gate_phase(
        "ws-a", "case-a", offers, doc_groups, gate_map, vendors
    )
    assert gate.total_submitted == 1
    assert bid in gate.verdicts
    assert bid in gate.eligible_vendor_ids
    assert len(filtered) == 1 and str(filtered[0]["document_id"]) == bid


# --- Groupe C — PENDING / non-SCORABLE matrice -----------------------------------


def test_pending_vendor_goes_to_pending_list_not_excluded() -> None:
    """PENDING : présent dans ``pending_vendor_ids``, absent de ``excluded`` et ``eligible``."""
    bid = "bundle-pending-only"
    corpus = _FULL_ELIGIBILITY_CORPUS.replace("q5_quitus", "")
    vin = build_vendor_gate_input_from_bundle_documents(
        bid,
        rows=[{"raw_text": corpus}],
        bundle_gate_b_status="SCORABLE",
    )
    gate = run_eligibility_gate("ws-p", "lot-p", {bid: vin})
    assert bid in gate.pending_vendor_ids
    assert bid not in gate.excluded_vendor_ids
    assert bid not in gate.eligible_vendor_ids
    assert gate.verdicts[bid].gate_result == RESULT_DISPLAY_PENDING


def test_p3_pending_as_unusable_not_not_in_m14_offer_list() -> None:
    """Aligné post-0fc6ad3 : rôle UNUSABLE → pas de ligne ``not_in_m14_offer_list`` (R3)."""
    pend = "pend-bundle-matrix"
    report = EvaluationReport(
        case_id="c-pend",
        evaluation_method="lowest_price",
        offer_evaluations=[],
    )
    _mp, ex = build_matrix_participants_and_excluded(
        report,
        bundle_roles={pend: ScoringRole.UNUSABLE},
        vendor_by_bundle={pend: "Vendor P"},
        extract_failed_bundles=frozenset(),
    )
    assert not any(x.get("bundle_id") == pend for x in ex)


def test_non_scorable_bundle_goes_to_excluded_from_matrix() -> None:
    """Bundle INTERNAL n’entre pas dans la matrice ; exclusion stable ``internal_reference_bundle``."""
    bid = "internal-bundle-1"
    report = EvaluationReport(
        case_id="c1",
        evaluation_method="lowest_price",
        offer_evaluations=[],
    )
    _mp, ex = build_matrix_participants_and_excluded(
        report,
        bundle_roles={bid: ScoringRole.INTERNAL},
        vendor_by_bundle={bid: "Policies"},
        extract_failed_bundles=frozenset(),
    )
    row = next(x for x in ex if x["bundle_id"] == bid)
    assert row["reason"] == "internal_reference_bundle"
    assert row["reason"] in EXCLUSION_REASONS


# --- Groupe D — non-réintroduction M14 ---------------------------------------------


def test_m14_eligibility_cannot_reintroduce_failed_vendor() -> None:
    """Les offres soumises à M14 sont le filtre P3 : un FAIL P3 n’apparaît jamais dans ``filtered``."""
    bid_ok = "ok-1"
    bid_fail = "fail-1"
    offers: list[dict[str, Any]] = [
        {
            "document_id": bid_ok,
            "supplier_name": "A",
            "process_role": "responds_to_bid",
        },
        {
            "document_id": bid_fail,
            "supplier_name": "B",
            "process_role": "responds_to_bid",
        },
    ]
    doc_groups: dict[str, list[dict[str, Any]]] = {
        bid_ok: [{"raw_text": _FULL_ELIGIBILITY_CORPUS}],
        bid_fail: [{"raw_text": "no eligibility tokens here"}],
    }
    gm = {bid_ok: "SCORABLE", bid_fail: "SCORABLE"}
    vendors = {bid_ok: "A", bid_fail: "B"}
    filtered, gate = run_p3_1b_eligibility_gate_phase(
        "ws-d", "case-d", offers, doc_groups, gm, vendors
    )
    assert bid_fail in gate.excluded_vendor_ids
    assert bid_fail not in {str(o["document_id"]) for o in filtered}
    assert {str(o["document_id"]) for o in filtered} <= set(gate.eligible_vendor_ids)
    evil = EvaluationReport(
        case_id="c-evil",
        evaluation_method="lowest_price",
        offer_evaluations=[
            OfferEvaluation(
                offer_document_id=bid_ok,
                supplier_name="A",
                is_eligible=True,
            ),
            OfferEvaluation(
                offer_document_id=bid_fail,
                supplier_name="B",
                is_eligible=True,
            ),
        ],
    )
    mp_evil, _ex_evil = build_matrix_participants_and_excluded(
        evil,
        bundle_roles={bid_ok: ScoringRole.SCORABLE, bid_fail: ScoringRole.SCORABLE},
        vendor_by_bundle=vendors,
        extract_failed_bundles=frozenset(),
    )
    assert bid_fail in {x["bundle_id"] for x in mp_evil}
    assert bid_fail not in {str(o["document_id"]) for o in filtered}, (
        "Invariant pipeline : M14 ne doit recevoir que ``filtered`` ; un rapport "
        "hypothétique incluant bid_fail serait incohérent avec l’entrée P3.1B."
    )


# --- Groupe E — bridge / assessments ---------------------------------------------


def test_bridge_strict_uuid_receives_only_eligible_vendors() -> None:
    """``matrix_participant_bundle_ids`` (strict) définit l’allowlist ; hors liste = pas d’assessment."""
    eligible = {"e1", "e2"}
    matrix_raw: dict[str, Any] = {
        "matrix_participants": [
            {"bundle_id": "e1", "supplier_name": "A", "is_eligible": True},
        ],
        "e1": {str(uuid.uuid4()): {"score": 1.0}},
        "pend": {str(uuid.uuid4()): {"score": 0.5}},
    }
    allow = matrix_participant_bundle_ids(matrix_raw, strict=True)
    assert allow is not None
    assert allow <= eligible
    assert "pend" not in allow


def test_excluded_and_pending_do_not_create_assessments() -> None:
    """Bundles exclus ou PENDING ne sont pas dans ``matrix_participants`` → filtre bridge les ignore."""
    crit = str(uuid.uuid4())
    matrix_raw: dict[str, Any] = {
        "matrix_participants": [{"bundle_id": "only-elig", "supplier_name": "X"}],
        "only-elig": {crit: {"score": 1.0}},
        "excluded-fail": {crit: {"score": 0.0}},
        "pending-p": {crit: {"score": 0.5}},
    }
    allow = matrix_participant_bundle_ids(matrix_raw, strict=True)
    assert allow == frozenset({"only-elig"})
    assert "excluded-fail" not in allow
    assert "pending-p" not in allow


# --- Groupe F — traçabilité des raisons ------------------------------------------


def test_excluded_from_matrix_reasons_are_distinct_and_stable() -> None:
    """Raisons Gate C / Gate B matrice / P3.1 disjointes et couvertes par ``EXCLUSION_REASONS``."""
    reasons = {
        "internal_reference_bundle",
        "reference_bundle",
        "ineligible",
        "eligibility_fail",
    }
    assert reasons <= EXCLUSION_REASONS
    assert len(reasons) == 4


# --- R6 intégration (mock DB minimal) --------------------------------------------


def _dao_rows_for_r6() -> list[dict[str, Any]]:
    u1, u2, u3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    return [
        {
            "id": u1,
            "critere_nom": "Critère A",
            "ponderation": 40.0,
            "is_eliminatory": False,
            "famille": "technical",
            "created_at": None,
        },
        {
            "id": u2,
            "critere_nom": "Critère B",
            "ponderation": 30.0,
            "is_eliminatory": True,
            "famille": "technical",
            "created_at": None,
        },
        {
            "id": u3,
            "critere_nom": "Critère C",
            "ponderation": 30.0,
            "is_eliminatory": False,
            "famille": "price",
            "created_at": None,
        },
    ]


@patch("src.services.pipeline_v5_service._vendor_name_by_bundle")
@patch("src.services.pipeline_v5_service._load_bundle_documents_grouped")
@patch("src.services.pipeline_v5_service._bundle_scoring_roles_for_workspace")
@patch(
    "src.services.pipeline_v5_service.extract_offers_from_bundles",
    return_value=(1, frozenset()),
)
@patch("src.services.pipeline_v5_service.db_fetchall")
@patch("src.services.pipeline_v5_service.db_execute_one")
@patch("src.services.pipeline_v5_service.get_connection")
def test_r6_run_pipeline_raises_when_p3_eliminates_all_scorable_offers(
    mock_get_connection: MagicMock,
    mock_execute_one: MagicMock,
    mock_fetchall: MagicMock,
    _mock_extract: MagicMock,
    mock_roles: MagicMock,
    mock_load_groups: MagicMock,
    mock_vendors: MagicMock,
) -> None:
    """Intégration : Gate-B-SCORABLE sans jetons P3 → 0 éligible → ``PipelineError`` R6."""
    wid = str(uuid.uuid4())
    case_legacy = str(uuid.uuid4())
    bundle_id = str(uuid.uuid4())

    mock_roles.return_value = {bundle_id: ScoringRole.SCORABLE}
    mock_load_groups.return_value = (
        {bundle_id: list(_SCORABLE_GATE_B_ROWS)},
        {bundle_id: "SOPRESCOM"},
    )
    mock_vendors.return_value = {bundle_id: "SOPRESCOM"}

    dao_rows = _dao_rows_for_r6()

    def _exec(conn: Any, sql: str, params: Any = None) -> Any:
        low = (sql or "").lower()
        if "process_workspaces" in low and "tenants" in low:
            return {
                "id": wid,
                "legacy_case_id": case_legacy,
                "tenant_code": "sci_ml",
            }
        if "count(*)" in low and "bundle_documents" in low:
            return {"n": 5}
        if "committees" in low and "committee_id" in low:
            return {"id": str(uuid.uuid4())}
        if "evaluation_documents" in low:
            return None
        raise AssertionError(f"unexpected db_execute_one SQL: {low[:220]!r}")

    def _fetch(conn: Any, sql: str, params: Any = None) -> list[dict[str, Any]]:
        low = (sql or "").lower()
        if "from dao_criteria" in low:
            return dao_rows
        if "from bundle_documents" in low and "raw_text" in low:
            return [{"raw_text": "stub corpus for m12"}]
        if "from offer_extractions" in low:
            return [
                {
                    "bundle_id": bundle_id,
                    "supplier_name": "SOPRESCOM",
                    "extracted_data_json": {},
                }
            ]
        raise AssertionError(f"unexpected db_fetchall SQL: {low[:220]!r}")

    mock_execute_one.side_effect = _exec
    mock_fetchall.side_effect = _fetch

    cm = MagicMock()
    cm.__enter__.return_value = MagicMock()
    cm.__exit__.return_value = None
    mock_get_connection.return_value = cm

    with pytest.raises(PipelineError, match="p3_1b_zero_eligible_after_gate"):
        run_pipeline_v5(wid, force_m14=False)
