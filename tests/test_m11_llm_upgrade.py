"""
Tests ADR-M11-002 — LLM Tier-1 Upgrade
Zéro appel API réel — tout mocké.

Test 1 : TIER_1_MODEL == "mistral-large-latest"
Test 2 : TIER_1_OCR_MODEL == "mistral-ocr-latest"
Test 3 : mock Mistral Files API → texte extrait depuis response.pages
Test 4 : MIME non supporté + Azure absent → ValueError
"""

from __future__ import annotations

import importlib
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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


# ── Test 3 — Files API : upload → process(file_id) → delete ──────────────


def test_extract_mistral_ocr_pages_joined(tmp_path, monkeypatch):
    """Files API : upload + ocr.process(file_id) → texte depuis response.pages."""
    import src.extraction.engine as eng

    fake_pdf = tmp_path / "scan.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake content")

    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))

    # Patch _detect_mime_from_header directement (attribut module)
    monkeypatch.setattr(eng, "_detect_mime_from_header", lambda _: "application/pdf")
    monkeypatch.setattr(eng.os.path, "getsize", lambda _: 1024)

    # Mock client Files API
    page1 = SimpleNamespace(markdown="Page 1 TDR")
    page2 = SimpleNamespace(markdown="Page 2 Budget")
    mock_client = MagicMock()
    mock_client.files.upload.return_value = SimpleNamespace(id="file-abc123")
    mock_client.ocr.process.return_value = SimpleNamespace(
        pages=[page1, page2], text=None
    )
    mock_client.files.delete.return_value = None

    mock_mistralai = MagicMock()
    mock_mistralai.Mistral.return_value = mock_client

    orig = sys.modules.get("mistralai")
    sys.modules["mistralai"] = mock_mistralai
    try:
        raw_text, _ = eng._extract_mistral_ocr(str(fake_pdf))
    finally:
        if orig is None:
            sys.modules.pop("mistralai", None)
        else:
            sys.modules["mistralai"] = orig

    assert "Page 1" in raw_text
    assert "Page 2" in raw_text
    mock_client.files.upload.assert_called_once()
    mock_client.ocr.process.assert_called_once()
    # Cleanup garanti
    mock_client.files.delete.assert_called_once_with(file_id="file-abc123")


# ── Test 4 — MIME non supporté + Azure absent → ValueError ────────────────


def test_extract_mistral_ocr_raises_for_unsupported_mime_no_azure(
    tmp_path, monkeypatch
):
    """MIME non supporté + AZURE_FORM_RECOGNIZER_ENDPOINT absent → ValueError."""
    import src.extraction.engine as eng

    fake_file = tmp_path / "doc.xyz"
    fake_file.write_bytes(b"garbage content")

    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.delenv("AZURE_FORM_RECOGNIZER_ENDPOINT", raising=False)

    monkeypatch.setattr(
        eng, "_detect_mime_from_header", lambda _: "application/octet-stream"
    )
    monkeypatch.setattr(eng.os.path, "getsize", lambda _: 256)

    with pytest.raises(ValueError, match="non supporté"):
        eng._extract_mistral_ocr(str(fake_file))
