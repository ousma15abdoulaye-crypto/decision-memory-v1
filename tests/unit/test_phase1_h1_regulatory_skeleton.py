"""Phase 1 — P0-H1 : squelette réglementaire (H1) avant M13."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.procurement.document_ontology import (
    DocumentKindParent,
    ProcurementFamily,
    ProcurementFamilySub,
    ProcurementFramework,
)
from src.procurement.handoff_builder import (
    _read_sci_thresholds_framework_key_from_repo,
    build_handoffs,
)
from src.procurement.procedure_models import (
    M12Handoffs,
    ScoringStructureDetected,
)
from src.services.pipeline_v5_service import (
    PipelineError,
    _build_one_minimal_m12_output,
    _ensure_h1_regulatory_skeleton_present,
)


def test_h1_present_for_sci_tenant() -> None:
    hh = build_handoffs(
        DocumentKindParent.OFFER_COMBINED,
        ProcurementFramework.SCI,
        0.8,
        ProcurementFamily.GOODS,
        ProcurementFamilySub.GENERIC,
        [],
        None,
        "sustainability 10% durable procurement manual",
    )
    assert hh.regulatory_profile_skeleton is not None
    assert hh.regulatory_profile_skeleton.framework_detected == ProcurementFramework.SCI
    yaml_fw = _read_sci_thresholds_framework_key_from_repo()
    assert yaml_fw == "sci"
    assert any(
        s.startswith("regulatory_yaml_framework=")
        for s in hh.regulatory_profile_skeleton.sci_signals_detected
    )


def test_h1_present_for_workspace_fallback_case() -> None:
    """Bundle minimal (ITT + corpus) : H1 construit si le cadre hôte est connu."""
    scoring = ScoringStructureDetected(
        criteria=[],
        total_weight=0.0,
        ponderation_coherence="NOT_FOUND",
        confidence=1.0,
        evidence=[],
    )
    m12 = _build_one_minimal_m12_output(
        bundle_id="_workspace",
        document_kind=DocumentKindParent.ITT,
        text="conditions générales d'achat",
        procurement_framework=ProcurementFramework.SCI,
        scoring=scoring,
        classified_pass_entries=["m13_pick:fallback_empty"],
    )
    assert m12.handoffs.regulatory_profile_skeleton is not None
    assert (
        m12.handoffs.regulatory_profile_skeleton.framework_detected
        == ProcurementFramework.SCI
    )


def test_pipeline_fails_fast_when_h1_missing() -> None:
    base = _build_one_minimal_m12_output(
        bundle_id="b1",
        document_kind=DocumentKindParent.OFFER_COMBINED,
        text="x",
        procurement_framework=ProcurementFramework.SCI,
        scoring=None,
        classified_pass_entries=[],
    )
    bad = base.model_copy(
        update={
            "handoffs": M12Handoffs(
                regulatory_profile_skeleton=None,
                atomic_capability_skeleton=None,
                market_context_signal=None,
            ),
        }
    )
    with pytest.raises(
        PipelineError, match="pipeline_invalid:H1_regulatory_profile_skeleton_missing"
    ):
        _ensure_h1_regulatory_skeleton_present(bad)


def test_m13_never_called_without_h1() -> None:
    """Fail-fast est placé avant l'instanciation de ``RegulatoryComplianceEngine``."""
    pipeline_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "services"
        / "pipeline_v5_service.py"
    )
    src = pipeline_path.read_text(encoding="utf-8")
    marker_fail = "pipeline_invalid:H1_regulatory_profile_skeleton_missing"
    marker_engine = "engine_m13 = RegulatoryComplianceEngine("
    assert marker_fail in src and marker_engine in src
    assert src.index(marker_fail) < src.index(marker_engine)


def test_regulatory_yaml_framework_line_exists() -> None:
    """Contenu réel du YAML SCI (pas de valeur inventée)."""
    yaml_path = (
        Path(__file__).resolve().parents[2]
        / "config"
        / "regulatory"
        / "sci"
        / "thresholds.yaml"
    )
    assert yaml_path.is_file()
    first = yaml_path.read_text(encoding="utf-8").splitlines()[0].strip()
    assert first == "framework: sci"
