"""Integration tests for Pass 1C — conformity + handoffs."""

from __future__ import annotations

import uuid

from src.annotation.pass_output import PassRunStatus
from src.annotation.passes.pass_1c_conformity_and_handoffs import (
    run_pass_1c_conformity_and_handoffs,
)
from src.procurement.procedure_models import DocumentValidity, TracedField


def _make_validity_dict() -> dict:
    v = DocumentValidity(
        document_validity_status=TracedField(
            value="valid", confidence=0.85, evidence=["test"]
        ),
        mandatory_detected_count=5,
        mandatory_total_count=5,
        mandatory_coverage=1.0,
    )
    return v.model_dump(mode="json")


class TestPass1C:
    def test_tdr_conformity(self) -> None:
        out = run_pass_1c_conformity_and_handoffs(
            normalized_text="Save the Children conditions générales d'achat NIF RCCM",
            document_id="test-doc-1c-001",
            run_id=uuid.uuid4(),
            document_kind_str="tdr",
            is_composite="no",
            validity_dict=_make_validity_dict(),
            framework_str="sci",
            framework_confidence=0.85,
            family_str="consultancy",
            family_sub_str="generic",
        )
        assert out.status in (PassRunStatus.SUCCESS, PassRunStatus.DEGRADED)
        assert "m12_conformity" in out.output_data
        assert "m12_handoffs" in out.output_data

    def test_handoffs_for_source_rules(self) -> None:
        out = run_pass_1c_conformity_and_handoffs(
            normalized_text="Dossier d'appel d'offres critères technique 70 points prix 30 points",
            document_id="test-doc-1c-002",
            run_id=uuid.uuid4(),
            document_kind_str="dao",
            is_composite="no",
            validity_dict=_make_validity_dict(),
            framework_str="sci",
            framework_confidence=0.80,
            family_str="goods",
            family_sub_str="generic",
        )
        handoffs = out.output_data.get("m12_handoffs", {})
        assert handoffs.get("regulatory_profile_skeleton") is not None
        assert handoffs.get("atomic_capability_skeleton") is not None
