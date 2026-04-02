"""Smoke tests for M14 EvaluationEngine (deterministic, no network)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.procurement.m14_engine import EvaluationEngine
from src.procurement.m14_evaluation_models import (
    EvaluationReport,
    M14EvaluationInput,
)

ALLOWED_CONFIDENCES = {0.6, 0.8, 1.0}

KILL_LIST_FIELDS = {"winner", "rank", "recommendation", "best_offer"}


def _minimal_input(**overrides: object) -> M14EvaluationInput:
    base: dict = {
        "case_id": "case-test-m14",
        "source_rules_document_id": "doc-source-1",
        "offers": [
            {
                "document_id": "offer-1",
                "supplier_name": "Supplier A",
                "process_role": "offer_technical",
                "present_admin_subtypes": ["nif", "rccm"],
                "capability_sections_present": ["methodology"],
                "currency": "XOF",
                "total_price": 5_000_000,
            },
        ],
        "h2_capability_skeleton": {
            "procurement_family": "goods",
            "procurement_family_sub": "generic",
            "active_capability_sections": ["methodology", "workplan"],
            "scoring_structure": {
                "criteria": [
                    {"criteria_name": "methodology", "weight_percent": 60.0},
                    {"criteria_name": "experience", "weight_percent": 40.0},
                ],
                "ponderation_coherence": "OK",
            },
        },
        "h3_market_context": {
            "prices_detected": True,
            "currency_detected": "XOF",
            "material_price_index_applicable": False,
            "material_categories_detected": [],
            "zone_for_price_reference": ["bamako"],
        },
        "rh1_compliance_checklist": {
            "per_offer_checks": [
                {
                    "check_id": "G-NIF",
                    "check_name": "NIF",
                    "verification_method": "document_presence",
                    "is_eliminatory": True,
                    "expected_admin_subtype": "nif",
                },
                {
                    "check_id": "G-RCCM",
                    "check_name": "RCCM",
                    "verification_method": "document_presence",
                    "is_eliminatory": True,
                    "expected_admin_subtype": "rccm",
                },
            ],
            "case_level_checks": [
                {
                    "check_id": "CL-1",
                    "check_name": "Minimum bids",
                    "is_eliminatory": False,
                },
            ],
        },
        "rh2_evaluation_blueprint": {
            "evaluation_method": "mieux_disant",
            "technical_weight": 70.0,
            "financial_weight": 30.0,
            "procedure_requirements_ref": "m13_profile/case-test-m14/latest",
        },
    }
    base.update(overrides)
    return M14EvaluationInput(**base)


class TestM14EngineSmoke:
    def test_basic_evaluation_produces_report(self) -> None:
        engine = EvaluationEngine()
        inp = _minimal_input()
        report = engine.evaluate(inp)
        assert isinstance(report, EvaluationReport)
        assert report.case_id == "case-test-m14"
        assert report.evaluation_method == "mieux_disant"
        assert report.total_offers_evaluated == 1
        assert len(report.offer_evaluations) == 1

    def test_offer_eligibility_pass(self) -> None:
        engine = EvaluationEngine()
        inp = _minimal_input()
        report = engine.evaluate(inp)
        offer = report.offer_evaluations[0]
        assert offer.is_eligible is True
        assert all(
            r.result in ("PASS", "NOT_APPLICABLE", "INDETERMINATE")
            for r in offer.eligibility_results
        )

    def test_offer_eligibility_fail_missing_doc(self) -> None:
        engine = EvaluationEngine()
        inp = _minimal_input(
            offers=[
                {
                    "document_id": "offer-fail",
                    "supplier_name": "Supplier B",
                    "present_admin_subtypes": [],
                }
            ]
        )
        report = engine.evaluate(inp)
        offer = report.offer_evaluations[0]
        assert offer.is_eligible is False

    def test_completion_analysis(self) -> None:
        engine = EvaluationEngine()
        inp = _minimal_input()
        report = engine.evaluate(inp)
        ca = report.offer_evaluations[0].completion_analysis
        assert ca is not None
        assert "methodology" in ca.present_sections
        assert "workplan" in ca.missing_sections
        assert ca.completeness_ratio == 0.5

    def test_technical_score_present(self) -> None:
        engine = EvaluationEngine()
        inp = _minimal_input()
        report = engine.evaluate(inp)
        ts = report.offer_evaluations[0].technical_score
        assert ts is not None
        assert len(ts.criteria_scores) == 2

    def test_price_analysis(self) -> None:
        engine = EvaluationEngine()
        inp = _minimal_input()
        report = engine.evaluate(inp)
        pa = report.offer_evaluations[0].price_analysis
        assert pa is not None
        assert pa.currency == "XOF"
        assert pa.currency_mismatch_alert is False

    def test_price_currency_mismatch_flagged(self) -> None:
        engine = EvaluationEngine()
        inp = _minimal_input(
            offers=[
                {
                    "document_id": "offer-usd",
                    "currency": "USD",
                    "total_price": 10_000,
                }
            ]
        )
        report = engine.evaluate(inp)
        pa = report.offer_evaluations[0].price_analysis
        assert pa is not None
        assert pa.currency_mismatch_alert is True

    def test_case_level_checks(self) -> None:
        engine = EvaluationEngine()
        inp = _minimal_input()
        report = engine.evaluate(inp)
        assert len(report.case_level_checks) == 1
        assert report.case_level_checks[0].result == "INDETERMINATE"

    def test_no_offers_review_required(self) -> None:
        engine = EvaluationEngine()
        inp = _minimal_input(offers=[])
        report = engine.evaluate(inp)
        assert report.total_offers_evaluated == 0
        assert "no_offers_provided" in report.m14_meta.review_reasons

    def test_extra_forbid_rejects_unknown_field(self) -> None:
        """E-49: extra='forbid' on M14 models rejects unknown fields."""
        engine = EvaluationEngine()
        inp = _minimal_input()
        report = engine.evaluate(inp)
        data = report.model_dump(mode="json")
        data["winner"] = "Supplier A"
        with pytest.raises(ValidationError):
            EvaluationReport.model_validate(data)

    def test_kill_list_fields_absent(self) -> None:
        """RÈGLE-09: winner / rank / recommendation / best_offer never in output."""
        engine = EvaluationEngine()
        inp = _minimal_input()
        report = engine.evaluate(inp)
        data = report.model_dump(mode="json")
        for field_name in KILL_LIST_FIELDS:
            assert field_name not in data, f"{field_name} found in EvaluationReport"

    def test_all_confidences_in_allowed_set(self) -> None:
        engine = EvaluationEngine()
        inp = _minimal_input()
        report = engine.evaluate(inp)
        confidences = _collect_confidences(report.model_dump(mode="json"))
        for c in confidences:
            assert (
                c in ALLOWED_CONFIDENCES
            ), f"confidence={c} not in {ALLOWED_CONFIDENCES}"


def _collect_confidences(obj: object) -> list[float]:
    found: list[float] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "confidence" and isinstance(v, int | float):
                found.append(float(v))
            else:
                found.extend(_collect_confidences(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_collect_confidences(item))
    return found
