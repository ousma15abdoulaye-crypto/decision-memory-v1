"""Tests for src/procurement/process_linker.py — L7 process linking."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

from src.procurement.document_ontology import (
    DocumentKindParent,
    ProcessRole,
)
from src.procurement.process_linker import (
    DocumentSummary,
    _load_fuzzy_threshold,
    build_process_linking,
    extract_procedure_references,
    extract_suppliers,
    link_documents,
)


def _make_summary(
    doc_id: str,
    kind: DocumentKindParent,
    ref: str | None = None,
    project: str | None = None,
    zones: list[str] | None = None,
) -> DocumentSummary:
    return DocumentSummary(
        document_id=doc_id,
        document_kind=kind,
        procedure_reference=ref,
        issuing_entity=None,
        project_name=project,
        zones=zones or [],
        submission_deadline=None,
    )


class TestExtractProcedureReferences:
    def test_extracts_ref(self) -> None:
        text = "Référence: SCI-PROC-2024-001 pour le marché de fournitures"
        refs = extract_procedure_references(text)
        assert len(refs) >= 1
        assert any("SCI-PROC-2024-001" in r for r in refs)

    def test_empty_text(self) -> None:
        assert extract_procedure_references("") == []


class TestExtractSuppliers:
    def test_detects_supplier(self) -> None:
        text = "Fournisseur: ABC SARL\nSoumissionnaire: DEF SA"
        suppliers = extract_suppliers(text)
        assert len(suppliers) >= 1

    def test_empty_text(self) -> None:
        assert extract_suppliers("") == []


class TestLinkDocuments:
    def test_exact_reference_link(self) -> None:
        source = _make_summary(
            "doc1", DocumentKindParent.OFFER_TECHNICAL, ref="SCI-001"
        )
        target = _make_summary("doc2", DocumentKindParent.TDR, ref="SCI-001")
        hints = link_documents(source, [target])
        assert len(hints) == 1
        assert hints[0].link_level == "EXACT_REFERENCE"
        assert hints[0].confidence >= 0.90

    def test_no_link_same_doc(self) -> None:
        source = _make_summary("doc1", DocumentKindParent.TDR, ref="REF-001")
        hints = link_documents(source, [source])
        assert len(hints) == 0

    def test_subject_temporal_link(self) -> None:
        source = _make_summary(
            "doc1", DocumentKindParent.OFFER_TECHNICAL, project="Water project"
        )
        target = _make_summary(
            "doc2", DocumentKindParent.TDR, project="Water project Mali"
        )
        hints = link_documents(source, [target])
        assert len(hints) >= 1


class TestBuildProcessLinking:
    def test_contract_is_end_marker(self) -> None:
        source = _make_summary("doc1", DocumentKindParent.CONTRACT)
        linking = build_process_linking(source, [], "Contract text")
        assert linking.procedure_end_marker.value == "yes"

    def test_tdr_role_is_defines_need(self) -> None:
        source = _make_summary("doc1", DocumentKindParent.TDR)
        linking = build_process_linking(source, [], "TDR text")
        assert linking.process_role.value == ProcessRole.DEFINES_NEED


class TestLoadFuzzyThreshold:
    """Tests pour _load_fuzzy_threshold — chargement YAML + fallback."""

    def test_file_absent_returns_fallback_and_logs_warning(
        self, tmp_path, caplog
    ) -> None:
        missing = tmp_path / "absent.yaml"
        with patch(
            "src.procurement.process_linker.Path",
            side_effect=lambda *a: missing if "llm_arbitration" in str(a) else Path(*a),
        ):
            with caplog.at_level(
                logging.WARNING, logger="src.procurement.process_linker"
            ):
                result = _load_fuzzy_threshold(fallback=0.85)
        assert result == 0.85
        assert any(
            "absent" in r.message or "llm_arbitration" in r.message
            for r in caplog.records
        )

    def test_valid_yaml_returns_configured_value(self, tmp_path) -> None:
        yaml_file = tmp_path / "llm_arbitration.yaml"
        yaml_file.write_text(
            "thresholds:\n  process_linking:\n    trigger_below_fuzzy: 0.72\n",
            encoding="utf-8",
        )
        with patch(
            "src.procurement.process_linker._load_fuzzy_threshold",
            side_effect=lambda fallback=0.85: _load_fuzzy_threshold_with_path(
                yaml_file, fallback
            ),
        ):
            pass
        # Appel direct avec path patchée via monkeypatch interne
        import src.procurement.process_linker as pl_mod

        original = pl_mod.Path
        try:
            pl_mod.Path = lambda *a: yaml_file if "llm_arbitration" in str(a) else original(*a)  # type: ignore[assignment]
            result = _load_fuzzy_threshold(fallback=0.85)
        finally:
            pl_mod.Path = original
        assert result == 0.72

    def test_invalid_yaml_type_returns_fallback_and_logs_warning(
        self, tmp_path, caplog
    ) -> None:
        yaml_file = tmp_path / "llm_arbitration.yaml"
        yaml_file.write_text("- item1\n- item2\n", encoding="utf-8")

        import src.procurement.process_linker as pl_mod

        original = pl_mod.Path
        try:
            pl_mod.Path = lambda *a: yaml_file if "llm_arbitration" in str(a) else original(*a)  # type: ignore[assignment]
            with caplog.at_level(
                logging.WARNING, logger="src.procurement.process_linker"
            ):
                result = _load_fuzzy_threshold(fallback=0.85)
        finally:
            pl_mod.Path = original
        assert result == 0.85
        assert any(
            "invalide" in r.message or "list" in r.message for r in caplog.records
        )

    def test_exception_in_load_returns_fallback_and_logs_warning(self, caplog) -> None:
        import src.procurement.process_linker as pl_mod

        original = pl_mod.Path
        try:
            pl_mod.Path = lambda *a: (_ for _ in ()).throw(OSError("permission denied"))  # type: ignore[assignment]
            with caplog.at_level(
                logging.WARNING, logger="src.procurement.process_linker"
            ):
                result = _load_fuzzy_threshold(fallback=0.85)
        finally:
            pl_mod.Path = original
        assert result == 0.85
        assert any(
            "permission" in r.message.lower() or "impossible" in r.message
            for r in caplog.records
        )


def _load_fuzzy_threshold_with_path(yaml_path: Path, fallback: float = 0.85) -> float:
    """Helper pour tester _load_fuzzy_threshold avec un chemin custom."""
    try:
        import yaml  # type: ignore[import-untyped]

        if not yaml_path.exists():
            return fallback
        with yaml_path.open(encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        if not isinstance(cfg, dict):
            return fallback
        return float(
            cfg.get("thresholds", {})
            .get("process_linking", {})
            .get("trigger_below_fuzzy", fallback)
        )
    except Exception:
        return fallback
