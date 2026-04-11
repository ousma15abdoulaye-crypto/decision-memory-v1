"""M13 — résolution stricte, payload persisté, paliers DGMP."""

from __future__ import annotations

import pytest

from src.procurement.compliance_models_m13 import (
    M13RegulatoryResolutionError,
    RegulatoryProcedureType,
)
from src.procurement.document_ontology import ProcurementFramework
from src.procurement.m13_engine import RegulatoryComplianceEngine
from src.procurement.m13_persistence_payload import (
    build_m13_regulatory_profile_persist_payload,
)
from src.procurement.m13_regulatory_profile_repository import (
    M13RegulatoryProfileRepository,
)
from src.procurement.procedure_rules_dgmp_mali import determine_dgmp_procedure_tier
from tests.procurement.m13_test_fixtures import (
    minimal_m12_output_dgmp_mali_goods,
    minimal_m12_output_with_h1,
)


def test_m13_raises_when_procedure_type_unresolved() -> None:
    m12 = minimal_m12_output_with_h1(framework=ProcurementFramework.UNKNOWN)
    engine = RegulatoryComplianceEngine()
    with pytest.raises(M13RegulatoryResolutionError, match="procedure_type unresolved"):
        engine.process_m12(case_id="case-u1", document_id="doc-u1", m12=m12)


def test_m13_sci_resolves_non_unknown_procedure() -> None:
    m12 = minimal_m12_output_with_h1()
    engine = RegulatoryComplianceEngine()
    out = engine.process_m12(case_id="case-s1", document_id="doc-s1", m12=m12)
    assert out.report.regime.framework == ProcurementFramework.SCI
    assert out.report.regime.procedure_type != RegulatoryProcedureType.UNKNOWN


def test_m13_dgmp_mali_resolves_non_unknown_procedure() -> None:
    m12 = minimal_m12_output_dgmp_mali_goods()
    engine = RegulatoryComplianceEngine()
    out = engine.process_m12(case_id="case-d1", document_id="doc-d1", m12=m12)
    assert out.report.regime.framework == ProcurementFramework.DGMP_MALI
    assert out.report.regime.procedure_type == RegulatoryProcedureType.SIMPLIFIED


def test_persist_payload_mandatory_and_root_m13b_hooks() -> None:
    m12 = minimal_m12_output_with_h1()
    engine = RegulatoryComplianceEngine()
    out = engine.process_m12(case_id="case-p1", document_id="doc-p1", m12=m12)
    p = build_m13_regulatory_profile_persist_payload(
        out, case_id="case-p1", document_id="doc-p1"
    )
    assert p["schema_version"] == "m13_regulatory_profile_envelope_v1"
    assert p["case_id"] == "case-p1"
    assert p["document_id"] == "doc-p1"
    assert p["persisted_at"]
    idx = p["profile_index"]
    assert idx["framework"] == "sci"
    assert idx["framework_version"] == "regulatory_yaml_bundle_v1"
    assert idx["procedure_type"] != "unknown"
    assert isinstance(idx["rules_applied"], list) and len(idx["rules_applied"]) >= 1
    hook_keys = (
        "policy_sources",
        "framework_conflicts",
        "control_objectives",
        "derogations",
        "audit_assertions",
        "normative_evidence",
    )
    for key in hook_keys:
        assert key in p
        assert p[key] == []
        assert p["m13b"][key] == []


def test_determine_dgmp_procedure_tier_matches_yaml_goods() -> None:
    r = determine_dgmp_procedure_tier(20_000_000.0, "XOF", family_key="goods")
    assert r.procedure_tier == "simplified"


def test_repository_get_latest_returns_none_without_db(monkeypatch) -> None:
    def _boom(*_a, **_k):
        raise RuntimeError("no db")

    monkeypatch.setattr(
        "src.procurement.m13_regulatory_profile_repository.get_connection",
        _boom,
    )
    repo = M13RegulatoryProfileRepository()
    assert repo.get_latest("any-case") is None
