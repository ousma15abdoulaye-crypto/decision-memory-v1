"""Integration tests for Pass 1B — document validity."""

from __future__ import annotations

import uuid

from src.annotation.pass_output import PassRunStatus
from src.annotation.passes.pass_1b_document_validity import (
    run_pass_1b_document_validity,
)


class TestPass1B:
    def test_tdr_validity(self) -> None:
        text = (
            "OBJECTIF de la mission: évaluation WASH.\n"
            "Périmètre: 5 régions du Mali.\n"
            "Livrables attendus: rapport final, base de données.\n"
            "Profil du consultant: 10 ans d'expérience.\n"
            "Modalités de soumission: envoyer par email."
        )
        out = run_pass_1b_document_validity(
            normalized_text=text,
            document_id="test-doc-1b-001",
            run_id=uuid.uuid4(),
            document_kind="tdr",
        )
        assert out.status in (PassRunStatus.SUCCESS, PassRunStatus.DEGRADED)
        assert "m12_validity" in out.output_data

    def test_unknown_kind_not_assessable(self) -> None:
        out = run_pass_1b_document_validity(
            normalized_text="Some random text.",
            document_id="test-doc-1b-002",
            run_id=uuid.uuid4(),
            document_kind="nonexistent_type",
        )
        assert out.status in (PassRunStatus.SUCCESS, PassRunStatus.DEGRADED)

    def test_has_coverage_data(self) -> None:
        text = "OBJECTIF de la mission.\nLivrables: rapport."
        out = run_pass_1b_document_validity(
            normalized_text=text,
            document_id="test-doc-1b-003",
            run_id=uuid.uuid4(),
            document_kind="tdr",
        )
        assert "mandatory_coverage" in out.output_data
        assert isinstance(out.output_data.get("mandatory_coverage"), float)
