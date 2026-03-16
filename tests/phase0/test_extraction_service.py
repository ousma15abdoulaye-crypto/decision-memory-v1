# tests/phase0/test_extraction_service.py
"""
Tests unitaires — ExtractionEngine service.
M-EXTRACTION-ENGINE ÉTAPE 3.
🔴 BLOQUANTS CI.
Constitution V3.3.2 §9 (doctrine échec).
ADR-0002 §2.5 (SLA deux classes).
"""

import os
import struct
import sys

import pytest

from src.extraction.engine import (
    _MISTRAL_OCR_MAX_BYTES,
    SLA_A_METHODS,
    SLA_B_METHODS,
    _compute_confidence,
    _extract_mistral_ocr,
    detect_method,
    extract_async,
    extract_sync,
    process_extraction_job,
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


# ── Classe 5 — _extract_mistral_ocr guards ──────────────────────


class TestMistralOCRGuards:
    """Garde-fous MIME type et taille pour Mistral OCR."""

    def _make_png_file(self, tmp_path, size_bytes=100):
        """Crée un fichier PNG minimal dans tmp_path."""
        # Minimal valid PNG (8-byte signature + IHDR + IEND)
        png_sig = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        ihdr_crc = b"\x00" * 4
        ihdr_chunk = struct.pack(">I", 13) + b"IHDR" + ihdr_data + ihdr_crc
        iend_chunk = struct.pack(">I", 0) + b"IEND" + b"\x00" * 4
        content = png_sig + ihdr_chunk + iend_chunk
        # Pad to desired size
        if len(content) < size_bytes:
            content += b"\x00" * (size_bytes - len(content))
        f = tmp_path / "test.png"
        f.write_bytes(content)
        return str(f)

    def _make_pdf_file(self, tmp_path, size_bytes=100):
        """Crée un fichier PDF minimal dans tmp_path."""
        content = b"%PDF-1.4 minimal" + b"\x00" * max(0, size_bytes - 16)
        f = tmp_path / "test.pdf"
        f.write_bytes(content)
        return str(f)

    def test_rejects_pdf_mime_type(self, monkeypatch, tmp_path):
        """PDF → ValueError (Mistral OCR image-only)."""
        monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
        monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
        path = self._make_pdf_file(tmp_path)

        with pytest.raises(ValueError, match="image"):
            _extract_mistral_ocr(path)

    def test_rejects_oversized_file(self, monkeypatch, tmp_path):
        """Fichier > 20 MB → ValueError."""
        monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
        monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
        path = self._make_png_file(tmp_path, size_bytes=100)
        # Fake the file size via os.path.getsize
        monkeypatch.setattr(os.path, "getsize", lambda p: _MISTRAL_OCR_MAX_BYTES + 1)

        with pytest.raises(ValueError, match="volumineux"):
            _extract_mistral_ocr(path)

    def test_accepts_image_mime(self, monkeypatch, tmp_path):
        """Image PNG + API key → Files API upload+ocr (mock pour éviter 401 en CI)."""
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
        monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
        path = self._make_png_file(tmp_path)

        # Patch _detect_mime_from_header pour retourner image/png
        import src.extraction.engine as _eng

        monkeypatch.setattr(_eng, "_detect_mime_from_header", lambda _: "image/png")

        # Mock Mistral Files API (ADR-M11-002 — Mandat 2)
        mock_client = MagicMock()
        mock_client.files.upload.return_value = SimpleNamespace(id="file-test")
        mock_client.ocr.process.return_value = SimpleNamespace(
            pages=[SimpleNamespace(markdown="Texte extrait mock")], text=None
        )
        mock_client.files.delete.return_value = None
        mock_mistral_module = MagicMock()
        mock_mistral_module.Mistral.return_value = mock_client

        orig = sys.modules.get("mistralai")
        sys.modules["mistralai"] = mock_mistral_module
        try:
            raw_text, structured = _extract_mistral_ocr(path)
            assert raw_text == "Texte extrait mock"
            assert isinstance(structured, dict)
        finally:
            if orig is None:
                sys.modules.pop("mistralai", None)
            else:
                sys.modules["mistralai"] = orig

    def test_missing_api_key_raises(self, monkeypatch, tmp_path):
        """Pas de MISTRAL_API_KEY → APIKeyMissingError."""
        from src.core.api_keys import APIKeyMissingError

        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
        path = self._make_png_file(tmp_path)

        with pytest.raises(APIKeyMissingError):
            _extract_mistral_ocr(path)


# ── Classe 6 — process_extraction_job ────────────────────────────


class TestProcessExtractionJob:
    """process_extraction_job — FSM pending → processing → done | failed."""

    def test_job_not_found_raises(self, monkeypatch):
        """Job inexistant → ValueError."""
        import src.extraction.engine as eng

        def fake_get_db_cursor():
            import contextlib

            @contextlib.contextmanager
            def _ctx():
                class FakeCursor:
                    def execute(self, *a, **kw):
                        pass

                    def fetchone(self):
                        return None

                yield FakeCursor()

            return _ctx()

        monkeypatch.setattr(eng, "get_db_cursor", fake_get_db_cursor)

        with pytest.raises(ValueError, match="introuvable"):
            process_extraction_job("job-inexistant")

    def test_non_pending_job_raises(self, monkeypatch):
        """Job pas en pending → ValueError."""
        import src.extraction.engine as eng

        def fake_get_db_cursor():
            import contextlib

            @contextlib.contextmanager
            def _ctx():
                class FakeCursor:
                    def execute(self, *a, **kw):
                        pass

                    def fetchone(self):
                        return {
                            "id": "job-1",
                            "document_id": "doc-1",
                            "method": "tesseract",
                            "status": "done",
                            "storage_uri": "/tmp/test.pdf",
                            "case_id": None,
                        }

                yield FakeCursor()

            return _ctx()

        monkeypatch.setattr(eng, "get_db_cursor", fake_get_db_cursor)

        with pytest.raises(ValueError, match="pending"):
            process_extraction_job("job-1")

    def test_invalid_method_raises(self, monkeypatch):
        """Méthode inconnue → ValueError."""
        import src.extraction.engine as eng

        def fake_get_db_cursor():
            import contextlib

            @contextlib.contextmanager
            def _ctx():
                class FakeCursor:
                    def execute(self, *a, **kw):
                        pass

                    def fetchone(self):
                        return {
                            "id": "job-1",
                            "document_id": "doc-1",
                            "method": "unknown_method",
                            "status": "pending",
                            "storage_uri": "/tmp/test.pdf",
                            "case_id": None,
                        }

                yield FakeCursor()

            return _ctx()

        monkeypatch.setattr(eng, "get_db_cursor", fake_get_db_cursor)

        with pytest.raises(ValueError, match="SLA-B"):
            process_extraction_job("job-1")
