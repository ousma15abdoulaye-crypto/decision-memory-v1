"""
Tests extract_text_any — M-FIX-EXTRACT-02
Périmètre : PDF natif + fallback pdfminer + cas dégradés
OCR (Mistral / Tesseract) = hors scope — M10A
"""

from unittest.mock import MagicMock, patch

import pytest

from src.couche_a.extraction import (
    ExtractionInsufficientTextError,
    extract_text_any,
)


class TestExtractTextAny:

    def test_pdf_natif_pypdf_ok(self, tmp_path):
        """pypdf retourne > 100 chars → pdfminer non appelé"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        texte_attendu = "A" * 500

        with patch("pypdf.PdfReader") as mock_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = texte_attendu
            mock_reader.return_value.pages = [mock_page]

            result = extract_text_any(str(pdf_file))

        assert len(result) >= 100
        assert "A" * 100 in result

    def test_pdf_corrompu_insufficient_raises(self, tmp_path):
        """pypdf et pdfminer échouent → ExtractionInsufficientTextError (M-CONTAINMENT-01)"""
        pdf_file = tmp_path / "corrompu.pdf"
        pdf_file.write_bytes(b"NOT A PDF")

        with patch("pypdf.PdfReader", side_effect=Exception("EOF")):
            with patch(
                "pdfminer.high_level.extract_text",
                side_effect=Exception("pdfminer fail"),
            ):
                with pytest.raises(ExtractionInsufficientTextError):
                    extract_text_any(str(pdf_file))

    def test_pdf_court_fallback_pdfminer(self, tmp_path):
        """pypdf retourne < 100 chars → pdfminer appelé et retourne plus"""
        pdf_file = tmp_path / "court.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        texte_court = "X" * 50  # pypdf — trop court
        texte_long = "Y" * 2000  # pdfminer — meilleur

        with patch("pypdf.PdfReader") as mock_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = texte_court
            mock_reader.return_value.pages = [mock_page]

            with patch(
                "pdfminer.high_level.extract_text",
                return_value=texte_long,
            ):
                result = extract_text_any(str(pdf_file))

        assert len(result) >= 100
        assert "Y" in result

    def test_doc_legacy_raises(self, tmp_path):
        """Fichier .doc binaire — non supporté → ExtractionInsufficientTextError"""
        doc_file = tmp_path / "legacy.doc"
        doc_file.write_bytes(b"\xd0\xcf\x11\xe0 fake ole")
        with pytest.raises(ExtractionInsufficientTextError):
            extract_text_any(str(doc_file))

    def test_pdf_scan_insufficient_raises(self, tmp_path, caplog):
        """PDF scan → texte nul → ExtractionInsufficientTextError"""
        pdf_file = tmp_path / "scan.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        with patch("pypdf.PdfReader") as mock_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = ""
            mock_reader.return_value.pages = [mock_page]

            with patch(
                "pdfminer.high_level.extract_text",
                return_value="",
            ):
                with caplog.at_level("WARNING"):
                    with pytest.raises(ExtractionInsufficientTextError):
                        extract_text_any(str(pdf_file))

        assert "PDF_SCAN_SANS_OCR" in caplog.text or "INSUFFICIENT_TEXT" in caplog.text

    def test_docx_extrait_correctement(self, tmp_path):
        """DOCX → python-docx appelé"""
        docx_file = tmp_path / "test.docx"
        docx_file.write_bytes(b"fake docx content")

        texte_attendu = "Contenu DOCX extrait correctement " * 10

        with patch("docx.Document") as mock_doc:
            mock_para = MagicMock()
            mock_para.text = texte_attendu
            mock_doc.return_value.paragraphs = [mock_para]

            result = extract_text_any(str(docx_file))

        assert texte_attendu in result

    def test_pdf_llamaparse_priority_long_text(self, tmp_path, monkeypatch):
        """LlamaParse priorité 1 : texte > 5000 car. sans passer par pypdf."""
        pdf_file = tmp_path / "lp.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        long_text = "Z" * 5200

        monkeypatch.setattr(
            "src.couche_a.extraction._try_llamaparse_pdf_first",
            lambda _fp: long_text,
        )

        with patch("pypdf.PdfReader", side_effect=AssertionError("pypdf ne doit pas s'exécuter")):
            result = extract_text_any(str(pdf_file))

        assert len(result) > 5000

    def test_plain_text_too_short_raises(self, tmp_path):
        """Fichier texte brut < MIN_EXTRACTED_TEXT_CHARS_FOR_ML → erreur explicite"""
        p = tmp_path / "short.txt"
        p.write_text("trois mots", encoding="utf-8")
        with pytest.raises(ExtractionInsufficientTextError):
            extract_text_any(str(p))
