"""Integration tests for Pass 1A — core recognition."""

from __future__ import annotations

import uuid

from src.annotation.pass_output import PassRunStatus
from src.annotation.passes.pass_1a_core_recognition import (
    run_pass_1a_core_recognition,
)


class TestPass1A:
    def test_tdr_recognition(self) -> None:
        text = "TERMES DE RÉFÉRENCE\nObjectif de la mission: évaluer le programme WASH.\nSave the Children"
        out = run_pass_1a_core_recognition(
            normalized_text=text,
            document_id="test-doc-001",
            run_id=uuid.uuid4(),
        )
        assert out.status in (PassRunStatus.SUCCESS, PassRunStatus.DEGRADED)
        assert out.output_data.get("taxonomy_core") == "tdr"
        assert "m12_recognition" in out.output_data

    def test_financial_offer_recognition(self) -> None:
        text = "PROPOSITION FINANCIÈRE\nBordereau des prix\nTotal HT: 15 000 000 FCFA"
        out = run_pass_1a_core_recognition(
            normalized_text=text,
            document_id="test-doc-002",
            run_id=uuid.uuid4(),
        )
        assert out.status in (PassRunStatus.SUCCESS, PassRunStatus.DEGRADED)
        assert "offer_financial" in out.output_data.get("taxonomy_core", "")

    def test_empty_text_degraded(self) -> None:
        out = run_pass_1a_core_recognition(
            normalized_text="",
            document_id="test-doc-003",
            run_id=uuid.uuid4(),
        )
        assert out.status == PassRunStatus.DEGRADED
        assert out.output_data.get("taxonomy_core") == "unknown"

    def test_degraded_quality_caps_confidence(self) -> None:
        text = "TERMES DE RÉFÉRENCE\nObjectif de la mission"
        out = run_pass_1a_core_recognition(
            normalized_text=text,
            document_id="test-doc-004",
            run_id=uuid.uuid4(),
            quality_class="degraded",
        )
        routing_conf = out.output_data.get("routing_confidence", 1.0)
        assert routing_conf <= 0.80

    def test_backward_compatible_keys(self) -> None:
        text = "DEMANDE DE COTATION articles"
        out = run_pass_1a_core_recognition(
            normalized_text=text,
            document_id="test-doc-005",
            run_id=uuid.uuid4(),
        )
        assert "document_role" in out.output_data
        assert "routing_confidence" in out.output_data
        assert "routing_evidence" in out.output_data
        assert "matched_rule" in out.output_data

    def test_confidence_in_valid_grid(self) -> None:
        text = "TERMES DE RÉFÉRENCE\nObjectif"
        out = run_pass_1a_core_recognition(
            normalized_text=text,
            document_id="test-doc-006",
            run_id=uuid.uuid4(),
        )
        conf = out.output_data.get("routing_confidence")
        assert conf in (0.6, 0.8, 1.0)
