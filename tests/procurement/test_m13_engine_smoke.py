"""Smoke tests for M13 RegulatoryComplianceEngine (deterministic, no network)."""

from __future__ import annotations

from src.procurement.compliance_models_m13 import ProcurementPrinciple
from src.procurement.document_ontology import ProcurementFramework
from src.procurement.m13_engine import RegulatoryComplianceEngine
from src.procurement.ocds_coverage_builder import build_ocds_default
from tests.procurement.m13_test_fixtures import minimal_m12_output_with_h1


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
