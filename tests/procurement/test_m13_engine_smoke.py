"""Smoke tests for M13 RegulatoryComplianceEngine (deterministic, no network)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.procurement.compliance_models_m13 import (
    M13RegulatoryComplianceReport,
    ProcurementPrinciple,
    legacy_compliance_report_from_m13,
)
from src.procurement.document_ontology import ProcurementFramework
from src.procurement.m13_engine import RegulatoryComplianceEngine
from src.procurement.ocds_coverage_builder import build_ocds_default
from tests.procurement.m13_test_fixtures import minimal_m12_output_with_h1

ALLOWED_CONFIDENCES = {0.6, 0.8, 1.0}


class TestM13EngineSmoke:
    def test_process_m12_sci_produces_report_and_principles(self) -> None:
        m12 = minimal_m12_output_with_h1()
        engine = RegulatoryComplianceEngine()
        out = engine.process_m12(
            case_id="case-test-1", document_id="doc-test-1", m12=m12
        )
        assert out.report.regime.framework == ProcurementFramework.SCI
        assert out.report.procedure_requirements is not None
        assert isinstance(out.report.compliance_gates, list)
        assert out.report.gates_summary.total_gates == len(out.report.compliance_gates)
        assert len(out.report.principles_compliance_map.principles) == len(
            ProcurementPrinciple
        )
        assert out.report.ocds_process_coverage is not None

    def test_ocds_default_builds(self) -> None:
        o = build_ocds_default()
        assert o.total_phases >= 1
        assert isinstance(o.phases, list)

    def test_extra_forbid_rejects_unknown_field(self) -> None:
        """E-49: extra='forbid' on M13 Pydantic models rejects unknown fields."""
        m12 = minimal_m12_output_with_h1()
        engine = RegulatoryComplianceEngine()
        out = engine.process_m12(
            case_id="case-test-1", document_id="doc-test-1", m12=m12
        )
        report_data = out.report.model_dump(mode="json")
        report_data["totally_unknown_field"] = 42
        with pytest.raises(ValidationError):
            M13RegulatoryComplianceReport.model_validate(report_data)

    def test_confidence_floor_only_allowed_values(self) -> None:
        """All gate confidences in the report must be in {0.6, 0.8, 1.0}."""
        m12 = minimal_m12_output_with_h1()
        engine = RegulatoryComplianceEngine()
        out = engine.process_m12(
            case_id="case-test-1", document_id="doc-test-1", m12=m12
        )
        for gate in out.report.compliance_gates:
            assert gate.confidence in ALLOWED_CONFIDENCES, (
                f"Gate {gate.gate_name}: confidence={gate.confidence} "
                f"not in {ALLOWED_CONFIDENCES}"
            )
        assert out.report.regime.confidence in ALLOWED_CONFIDENCES

    def test_legacy_bridge_produces_valid_report(self) -> None:
        """legacy_compliance_report_from_m13 returns a well-formed legacy report."""
        m12 = minimal_m12_output_with_h1()
        engine = RegulatoryComplianceEngine()
        out = engine.process_m12(
            case_id="case-test-1", document_id="doc-test-1", m12=m12
        )
        legacy = legacy_compliance_report_from_m13(
            document_id="doc-test-1", m13=out.report
        )
        assert legacy.verdict is not None
        assert legacy.document_id == "doc-test-1"
        assert isinstance(legacy.eliminatory_checks, list)
