"""Integration tests for Pass 1D — process linking."""

from __future__ import annotations

import uuid

from src.annotation.pass_output import PassRunStatus
from src.annotation.passes.pass_1d_process_linking import (
    run_pass_1d_process_linking,
)


def _make_1a_output(doc_id: str, kind: str, ref: str | None = None) -> dict:
    return {
        "document_id": doc_id,
        "m12_recognition": {
            "document_kind": {"value": kind, "confidence": 0.90, "evidence": ["test"]},
            "procedure_reference_detected": {
                "value": ref,
                "confidence": 0.80 if ref else 0.0,
                "evidence": [],
            },
            "issuing_entity_detected": {
                "value": None,
                "confidence": 0.0,
                "evidence": [],
            },
            "project_name_detected": {
                "value": "Water WASH",
                "confidence": 0.70,
                "evidence": [],
            },
            "zone_scope_detected": {
                "value": ["Bamako"],
                "confidence": 0.70,
                "evidence": [],
            },
            "submission_deadline_detected": {
                "value": None,
                "confidence": 0.0,
                "evidence": [],
            },
        },
    }


class TestPass1D:
    def test_single_document_linking(self) -> None:
        out = run_pass_1d_process_linking(
            normalized_text="TERMES DE RÉFÉRENCE pour mission WASH",
            document_id="test-doc-1d-001",
            run_id=uuid.uuid4(),
            pass_1a_output_data=_make_1a_output("test-doc-1d-001", "tdr", "SCI-001"),
        )
        assert out.status == PassRunStatus.SUCCESS
        assert "m12_linking" in out.output_data
        assert "process_role" in out.output_data

    def test_case_level_linking(self) -> None:
        source_1a = _make_1a_output("doc-offer", "offer_technical", "SCI-001")
        case_docs = [
            _make_1a_output("doc-tdr", "tdr", "SCI-001"),
            _make_1a_output("doc-offer", "offer_technical", "SCI-001"),
        ]
        out = run_pass_1d_process_linking(
            normalized_text="Offre technique fournisseur ABC SARL référence SCI-001",
            document_id="doc-offer",
            run_id=uuid.uuid4(),
            pass_1a_output_data=source_1a,
            case_documents_1a=case_docs,
        )
        assert out.status == PassRunStatus.SUCCESS
        linking = out.output_data.get("m12_linking", {})
        assert linking.get("linked_parent_hint") is not None

    def test_no_case_docs_still_works(self) -> None:
        out = run_pass_1d_process_linking(
            normalized_text="Document isolé",
            document_id="doc-alone",
            run_id=uuid.uuid4(),
            pass_1a_output_data=_make_1a_output("doc-alone", "unknown"),
            case_documents_1a=None,
        )
        assert out.status == PassRunStatus.SUCCESS
