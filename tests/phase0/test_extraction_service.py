# tests/phase0/test_extraction_service.py
"""
Tests unitaires — ExtractionEngine service.
M-EXTRACTION-ENGINE ÉTAPE 3.
🔴 BLOQUANTS CI.
Constitution V3.3.2 §9 (doctrine échec).
ADR-0002 §2.5 (SLA deux classes).
"""

import pytest

from src.extraction.engine import (
    SLA_A_METHODS,
    SLA_B_METHODS,
    _compute_confidence,
    detect_method,
    extract_async,
    extract_sync,
)

# ── Classe 1 — detect_method ─────────────────────────────────────


class TestDetectMethod:
    """Détection méthode sur magic bytes réels."""

    def test_pdf_natif_avec_bt(self):
        """PDF avec marqueur BT → native_pdf."""
        content = b"%PDF-1.4 ... BT some text ET ..."
        result = detect_method("application/pdf", content)
        assert result == "native_pdf"

    def test_pdf_sans_bt_fallback_tesseract(self):
        """PDF sans BT (scan) → tesseract."""
        content = b"%PDF-1.4 no text markers here"
        result = detect_method("application/pdf", content)
        assert result == "tesseract"

    def test_xlsx_magic_bytes(self):
        """ZIP avec xl/ → excel_parser."""
        content = b"PK\x03\x04" + b"\x00" * 20 + b"xl/workbook"
        result = detect_method("application/vnd.ms-excel", content)
        assert result == "excel_parser"

    def test_docx_magic_bytes(self):
        """ZIP avec word/ → docx_parser."""
        content = b"PK\x03\x04" + b"\x00" * 20 + b"word/document"
        result = detect_method("application/vnd.openxmlformats", content)
        assert result == "docx_parser"

    def test_unknown_fallback_tesseract(self):
        """Contenu inconnu → tesseract (fallback)."""
        content = b"\x00\x01\x02\x03 unknown format"
        result = detect_method("application/octet-stream", content)
        assert result == "tesseract"


# ── Classe 2 — Validation SLA ────────────────────────────────────


class TestSLAValidation:
    """extract_sync/async refusent les mauvaises méthodes."""

    def test_extract_sync_rejette_methode_sla_b(self, monkeypatch):
        """
        extract_sync avec méthode SLA-B → ValueError immédiat.
        Pas de connexion DB nécessaire.
        """

        def fake_get_doc(doc_id):
            return {
                "id": doc_id,
                "mime_type": "image/tiff",
                "storage_uri": "/tmp/test.tif",
                "extraction_status": "pending",
                "extraction_method": "tesseract",
            }

        import src.extraction.engine as eng

        monkeypatch.setattr(eng, "get_document", fake_get_doc)

        with pytest.raises(ValueError) as exc:
            extract_sync("doc-test-001")
        assert "SLA-B" in str(exc.value)
        assert "extract_async" in str(exc.value)

    def test_extract_async_rejette_methode_sla_a(self):
        """
        extract_async avec méthode SLA-A → ValueError immédiat.
        Pas de connexion DB nécessaire.
        """
        with pytest.raises(ValueError) as exc:
            extract_async("doc-test-001", "native_pdf")
        assert "SLA-A" in str(exc.value)
        assert "extract_sync" in str(exc.value)

    def test_sla_a_methods_contient_trois_methodes(self):
        """SLA_A_METHODS = exactement 3 méthodes."""
        assert SLA_A_METHODS == {"native_pdf", "excel_parser", "docx_parser"}

    def test_sla_b_methods_contient_quatre_methodes(self):
        """SLA_B_METHODS = exactement 4 méthodes."""
        assert SLA_B_METHODS == {"tesseract", "azure", "llamaparse", "mistral_ocr"}


# ── Classe 3 — _compute_confidence ──────────────────────────────


class TestComputeConfidence:
    """§9 : incertitude mesurée, jamais masquée."""

    def test_texte_vide_confidence_03(self):
        """Texte vide → confidence 0.3."""
        score = _compute_confidence("", {})
        assert score == pytest.approx(0.3)

    def test_texte_trop_court_confidence_03(self):
        """Texte < 100 chars → confidence 0.3."""
        score = _compute_confidence("x" * 50, {})
        assert score == pytest.approx(0.3)

    def test_texte_court_confidence_06(self):
        """100 <= texte < 500 chars → confidence 0.6."""
        score = _compute_confidence("x" * 200, {})
        assert score == pytest.approx(0.6)

    def test_texte_long_confidence_085(self):
        """Texte >= 500 chars → confidence 0.85."""
        score = _compute_confidence("x" * 1000, {})
        assert score == pytest.approx(0.85)

    def test_texte_whitespace_seul_confidence_03(self):
        """Texte = espaces uniquement → confidence 0.3."""
        score = _compute_confidence("   \n\t  ", {})
        assert score == pytest.approx(0.3)


# ── Classe 4 — Doctrine §9 ───────────────────────────────────────


class TestDoctrineEchec:
    """
    §9 : incertitude signalée, échec explicite.
    Tests sans DB via monkeypatch.
    """

    def test_confidence_faible_flags_requires_human(self, monkeypatch):
        """
        confidence < 0.6 → _requires_human_review = True
        dans structured_data.
        """
        import src.extraction.engine as eng

        calls = {}

        def fake_get_doc(doc_id):
            return {
                "id": doc_id,
                "mime_type": "application/pdf",
                "storage_uri": "/tmp/test.pdf",
                "extraction_status": "pending",
                "extraction_method": "native_pdf",
            }

        def fake_dispatch(doc, method):
            # Texte court → confidence 0.3
            return ("x" * 10, dict(eng.STRUCTURED_DATA_EMPTY))

        def fake_update_status(doc_id, status):
            calls[f"status_{status}"] = True

        def fake_store_extraction(
            doc_id, raw_text, structured, method, confidence, case_id=None
        ):
            calls["structured"] = structured
            calls["confidence"] = confidence

        monkeypatch.setattr(eng, "get_document", fake_get_doc)
        monkeypatch.setattr(eng, "_dispatch_extraction", fake_dispatch)
        monkeypatch.setattr(eng, "_update_document_status", fake_update_status)
        monkeypatch.setattr(eng, "_store_extraction", fake_store_extraction)

        result = extract_sync("doc-test-low-conf")

        assert result["requires_human_review"] is True
        assert result["confidence"] < 0.6
        assert calls["structured"]["_low_confidence"] is True
        assert calls["structured"]["_requires_human_review"] is True

    def test_exception_store_error_appele(self, monkeypatch):
        """
        §9 : toute exception dans extract_sync
        → _store_error appelé + exception re-levée.
        """
        import src.extraction.engine as eng

        errors_stored = []

        def fake_get_doc(doc_id):
            return {
                "id": doc_id,
                "mime_type": "application/pdf",
                "storage_uri": "/tmp/test.pdf",
                "extraction_status": "pending",
                "extraction_method": "native_pdf",
            }

        def fake_dispatch(doc, method):
            raise RuntimeError("Parseur planté")

        def fake_update_status(doc_id, status):
            pass

        def fake_store_error(doc_id, job_id, error_code, detail):
            errors_stored.append(
                {
                    "error_code": error_code,
                    "detail": detail,
                }
            )

        monkeypatch.setattr(eng, "get_document", fake_get_doc)
        monkeypatch.setattr(eng, "_dispatch_extraction", fake_dispatch)
        monkeypatch.setattr(eng, "_update_document_status", fake_update_status)
        monkeypatch.setattr(eng, "_store_error", fake_store_error)

        with pytest.raises(RuntimeError, match="Parseur planté"):
            extract_sync("doc-test-exception")

        assert len(errors_stored) == 1
        assert errors_stored[0]["error_code"] == "PARSE_ERROR"
        assert "Parseur planté" in errors_stored[0]["detail"]
