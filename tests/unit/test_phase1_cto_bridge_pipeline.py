"""Phase 1 CTO — Gate A bridge / scoring role (sans DB Alembic)."""

from __future__ import annotations

from src.procurement.bundle_scoring_role import (
    ScoringRole,
    classify_bundle_scoring_role,
)
from src.procurement.document_ontology import ProcurementFramework
from src.procurement.m14_evaluation_models import EvaluationReport
from src.services.m14_bridge import (
    _flatten_evaluation_report_scores_matrix,
    matrix_participant_bundle_ids,
    scoring_criterion_key_is_forbidden,
)
from src.services.pipeline_v5_service import (
    build_matrix_participants_and_excluded,
    procurement_framework_from_tenant_code,
)


def test_gate_a_sci_mali_maps_sci() -> None:
    assert (
        procurement_framework_from_tenant_code("sci_mali") == ProcurementFramework.SCI
    )


def test_gate_a_sci_niger_maps_sci() -> None:
    assert (
        procurement_framework_from_tenant_code("sci_niger") == ProcurementFramework.SCI
    )


def test_gate_a_sci_bare_maps_sci() -> None:
    assert procurement_framework_from_tenant_code("sci") == ProcurementFramework.SCI


def test_gate_a_unknown_tenant_no_dgmp_fallback() -> None:
    assert (
        procurement_framework_from_tenant_code("acme_corp")
        == ProcurementFramework.UNKNOWN
    )


def test_scoring_criterion_key_forbidden_eligibility_compliance() -> None:
    assert scoring_criterion_key_is_forbidden("m14:eligibility:nif_expiry")
    assert scoring_criterion_key_is_forbidden("m14:compliance:art_12")
    assert scoring_criterion_key_is_forbidden("m14:technical:foo_bar")
    assert scoring_criterion_key_is_forbidden("m14:price")
    assert scoring_criterion_key_is_forbidden("reg_only_xyz")


def test_scoring_criterion_key_uuid_allowed() -> None:
    u = "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"
    assert not scoring_criterion_key_is_forbidden(u)


def test_flatten_does_not_emit_eligibility_matrix_keys() -> None:
    report: dict = {
        "offer_evaluations": [
            {
                "offer_document_id": "bundle-1",
                "technical_score": {
                    "criteria_scores": [
                        {
                            "criteria_name": "Critère test",
                            "awarded_score": 4.0,
                            "max_score": 10.0,
                            "weight_percent": 50.0,
                        }
                    ]
                },
                "eligibility_results": [
                    {"check_id": "k1", "result": "PASS", "check_name": "x"}
                ],
                "compliance_results": [
                    {"check_id": "k2", "result": "FAIL", "check_name": "y"}
                ],
            }
        ]
    }
    dao_id = "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"
    flat = _flatten_evaluation_report_scores_matrix(
        report,
        by_norm_name={"critère test": dao_id},
        by_code={},
    )
    per = flat["bundle-1"]
    assert not any(k.startswith("m14:eligibility:") for k in per)
    assert not any(k.startswith("m14:compliance:") for k in per)
    assert "m14:price" not in per
    assert dao_id in per


def test_scoring_role_scorable_with_offer_and_vendor() -> None:
    r = classify_bundle_scoring_role(
        vendor_name_raw="ACME",
        doc_types=frozenset({"offer_technical"}),
    )
    assert r == ScoringRole.SCORABLE


def test_scoring_role_unusable_offer_without_vendor() -> None:
    r = classify_bundle_scoring_role(
        vendor_name_raw="",
        doc_types=frozenset({"offer_technical"}),
    )
    assert r == ScoringRole.UNUSABLE


def test_scoring_role_internal_rfq_only() -> None:
    r = classify_bundle_scoring_role(
        vendor_name_raw="X",
        doc_types=frozenset({"rfq", "tdr"}),
    )
    assert r == ScoringRole.INTERNAL


def test_gate_c_matrix_participants_only_eligible() -> None:
    report = EvaluationReport.model_validate(
        {
            "case_id": "c1",
            "evaluation_method": "lowest_price",
            "offer_evaluations": [
                {
                    "offer_document_id": "b-elig",
                    "supplier_name": "OK Co",
                    "is_eligible": True,
                    "eligibility_results": [],
                    "compliance_results": [],
                    "flags": [],
                },
                {
                    "offer_document_id": "b-bad",
                    "supplier_name": "Bad Co",
                    "is_eligible": False,
                    "eligibility_results": [
                        {
                            "check_id": "k1",
                            "check_name": "NIF",
                            "result": "FAIL",
                            "is_eliminatory": True,
                            "evidence": [],
                            "confidence": 0.8,
                        }
                    ],
                    "compliance_results": [],
                    "flags": [],
                },
            ],
        }
    )
    mp, ex = build_matrix_participants_and_excluded(
        report,
        bundle_roles={},
        vendor_by_bundle={},
        extract_failed_bundles=frozenset(),
    )
    assert [x["bundle_id"] for x in mp] == ["b-elig"]
    assert any(x["bundle_id"] == "b-bad" and x["reason"] == "ineligible" for x in ex)


def test_gate_c_matrix_participant_ids_none_when_legacy_payload() -> None:
    assert matrix_participant_bundle_ids({"offer_evaluations": []}) is None


def test_gate_c_matrix_participant_ids_empty_set() -> None:
    assert matrix_participant_bundle_ids({"matrix_participants": []}) == frozenset()


def test_gate_c_excluded_extraction_failed_scorable_not_in_offer_list() -> None:
    """SCORABLE présent en DB mais absent de offer_evaluations → excluded_from_matrix."""
    report = EvaluationReport.model_validate(
        {
            "case_id": "c1",
            "evaluation_method": "lowest_price",
            "offer_evaluations": [
                {
                    "offer_document_id": "b1",
                    "supplier_name": "Only",
                    "is_eligible": True,
                    "eligibility_results": [],
                    "compliance_results": [],
                    "flags": [],
                },
            ],
        }
    )
    mp, ex = build_matrix_participants_and_excluded(
        report,
        bundle_roles={"b1": ScoringRole.SCORABLE, "b2": ScoringRole.SCORABLE},
        vendor_by_bundle={"b2": "Lost extract"},
        extract_failed_bundles=frozenset({"b2"}),
    )
    assert [x["bundle_id"] for x in mp] == ["b1"]
    assert any(
        x["bundle_id"] == "b2" and x["reason"] == "extraction_failed" for x in ex
    )
