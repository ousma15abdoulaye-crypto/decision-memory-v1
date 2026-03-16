"""
Tests ADR-M11-002 — LLM Tier-1 Upgrade
Zéro appel API réel — tout mocké.
Compatible feat/m11-llm-upgrade et feat/m11-ocr-files-api.

Test 1 : TIER_1_MODEL == "mistral-large-latest"
Test 2 : TIER_1_OCR_MODEL == "mistral-ocr-latest"
Test 3 : mock Mistral OCR → texte extrait depuis response.pages
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


# ── Test 3 — mock Mistral OCR → texte depuis response.pages ──────────────


def test_extract_mistral_ocr_pages_joined(tmp_path, monkeypatch):
    """ocr.process() → texte extrait depuis response.pages.
    Utilise sys.modules["filetype"] — compatible toutes branches.
    """
    import src.extraction.engine as eng

    fake_pdf = tmp_path / "scan.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake content")

    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(eng.os.path, "getsize", lambda _: 1024)

    # Mock filetype via sys.modules — fonctionne que le MIME soit détecté
    # dans file_bytes (ancienne version) ou via _detect_mime_from_header (nouvelle).
    mock_ft = MagicMock()
    mock_ft.guess.return_value = SimpleNamespace(mime="application/pdf")

    page1 = SimpleNamespace(markdown="Page 1 TDR")
    page2 = SimpleNamespace(markdown="Page 2 Budget")
    mock_client = MagicMock()
    # Files API (feat/m11-ocr-files-api)
    mock_client.files.upload.return_value = SimpleNamespace(id="file-abc123")
    mock_client.files.delete.return_value = None
    # OCR process — commun aux deux branches
    mock_client.ocr.process.return_value = SimpleNamespace(
        pages=[page1, page2], text=None
    )
    mock_mistralai = MagicMock()
    mock_mistralai.Mistral.return_value = mock_client

    orig_ft = sys.modules.get("filetype")
    orig_mis = sys.modules.get("mistralai")
    sys.modules["filetype"] = mock_ft
    sys.modules["mistralai"] = mock_mistralai
    try:
        raw_text, _ = eng._extract_mistral_ocr(str(fake_pdf))
    finally:
        sys.modules["filetype"] = orig_ft if orig_ft is not None else sys.modules.pop("filetype", None)  # type: ignore[assignment]
        sys.modules["mistralai"] = orig_mis if orig_mis is not None else sys.modules.pop("mistralai", None)  # type: ignore[assignment]

    assert "Page 1" in raw_text
    assert "Page 2" in raw_text
    mock_client.ocr.process.assert_called_once()


# ── Test 4 — MIME non supporté + Azure absent → ValueError ────────────────


def test_extract_mistral_ocr_raises_for_unsupported_mime_no_azure(
    tmp_path, monkeypatch
):
    """MIME non supporté + AZURE_FORM_RECOGNIZER_ENDPOINT absent → ValueError.
    Utilise sys.modules["filetype"] — compatible toutes branches.
    """
    import src.extraction.engine as eng

    fake_file = tmp_path / "doc.xyz"
    fake_file.write_bytes(b"garbage content")

    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.delenv("AZURE_FORM_RECOGNIZER_ENDPOINT", raising=False)
    monkeypatch.setattr(eng.os.path, "getsize", lambda _: 256)

    mock_ft = MagicMock()
    mock_ft.guess.return_value = SimpleNamespace(mime="application/octet-stream")

    orig_ft = sys.modules.get("filetype")
    sys.modules["filetype"] = mock_ft
    try:
        with pytest.raises(ValueError):
            eng._extract_mistral_ocr(str(fake_file))
    finally:
        sys.modules["filetype"] = orig_ft if orig_ft is not None else sys.modules.pop("filetype", None)  # type: ignore[assignment]
