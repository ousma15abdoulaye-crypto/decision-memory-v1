"""
Tests ADR-M11-002 — LLM Tier-1 Upgrade
Zéro appel API réel — tout mocké.

Test 1 : TIER_1_MODEL == "mistral-large-latest"
Test 2 : TIER_1_OCR_MODEL == "mistral-ocr-latest"
Test 3 : mock Mistral OCR → texte extrait depuis response.pages
Test 4 : MIME non supporté + Azure absent → ValueError
"""

from __future__ import annotations

import importlib
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# ── Test 1 — TIER_1_MODEL ─────────────────────────────────────────────────


def test_tier1_model_is_mistral_large():
    """TIER_1_MODEL doit être mistral-large-latest (défaut sans env override)."""
    backup = os.environ.pop("TIER_1_MODEL", None)
    try:
        import src.couche_a.llm_router as router

        importlib.reload(router)
        assert router.TIER_1_MODEL == "mistral-large-latest"
    finally:
        if backup is not None:
            os.environ["TIER_1_MODEL"] = backup


# ── Test 2 — TIER_1_OCR_MODEL ─────────────────────────────────────────────


def test_tier1_ocr_model_is_mistral_ocr_latest():
    """TIER_1_OCR_MODEL doit être mistral-ocr-latest (défaut sans env override)."""
    backup = os.environ.pop("TIER_1_OCR_MODEL", None)
    try:
        import src.couche_a.llm_router as router

        importlib.reload(router)
        assert router.TIER_1_OCR_MODEL == "mistral-ocr-latest"
    finally:
        if backup is not None:
            os.environ["TIER_1_OCR_MODEL"] = backup


# ── Test 3 — mock Mistral OCR → structure retour ──────────────────────────


def test_extract_mistral_ocr_pages_joined(tmp_path):
    """client.ocr.process() → texte concaténé depuis response.pages."""
    fake_pdf = tmp_path / "scan.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake")

    page1 = SimpleNamespace(markdown="Page 1 : Titre du marché")
    page2 = SimpleNamespace(markdown="Page 2 : Critères")
    mock_response = SimpleNamespace(pages=[page1, page2], text=None)

    mock_ocr_process = MagicMock(return_value=mock_response)
    mock_mistral_client = MagicMock()
    mock_mistral_client.ocr.process = mock_ocr_process

    mock_ft = MagicMock()
    mock_ft.guess.return_value = SimpleNamespace(mime="application/pdf")

    import src.extraction.engine as eng

    with (
        patch.object(eng, "get_mistral_api_key", return_value="fake-key"),
        patch("src.extraction.engine.os.path.getsize", return_value=1024),
        patch(
            "src.extraction.engine.open", mock_file_ctx(b"%PDF-1.4 fake"), create=True
        ),
        patch.dict("sys.modules", {"filetype": mock_ft}),
        patch("mistralai.Mistral", return_value=mock_mistral_client),
        patch("src.couche_a.llm_router.TIER_1_OCR_MODEL", "mistral-ocr-latest"),
        patch("src.extraction.engine.STORAGE_BASE_PATH", str(tmp_path)),
    ):
        raw_text, _ = eng._extract_mistral_ocr(str(fake_pdf))

    assert "Page 1" in raw_text
    assert "Page 2" in raw_text
    mock_ocr_process.assert_called_once()


# ── Test 4 — MIME non supporté + Azure absent → ValueError ────────────────


def test_extract_mistral_ocr_raises_for_unsupported_mime_no_azure(tmp_path):
    """MIME non supporté + AZURE_FORM_RECOGNIZER_ENDPOINT absent → ValueError."""
    fake_file = tmp_path / "doc.xyz"
    fake_file.write_bytes(b"garbage content")

    mock_ft = MagicMock()
    mock_ft.guess.return_value = SimpleNamespace(mime="application/octet-stream")

    import src.extraction.engine as eng

    with (
        patch.object(eng, "get_mistral_api_key", return_value="fake-key"),
        patch("src.extraction.engine.os.path.getsize", return_value=256),
        patch("src.extraction.engine.open", mock_file_ctx(b"garbage"), create=True),
        patch.dict("sys.modules", {"filetype": mock_ft}),
        patch.dict(os.environ, {"AZURE_FORM_RECOGNIZER_ENDPOINT": ""}),
        patch("src.extraction.engine.STORAGE_BASE_PATH", str(tmp_path)),
    ):
        try:
            eng._extract_mistral_ocr(str(fake_file))
            assert False, "ValueError attendue"
        except ValueError:
            pass  # attendu


# ── Helpers ───────────────────────────────────────────────────────────────


def mock_file_ctx(content: bytes):
    """Retourne un context manager mock pour open() retournant content."""
    m = MagicMock()
    m.__enter__ = MagicMock(
        return_value=MagicMock(read=MagicMock(return_value=content))
    )
    m.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=m)
