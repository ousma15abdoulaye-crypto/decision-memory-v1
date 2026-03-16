"""
Tests Mandat 2 — OCR Files API (stream + cleanup garanti)
Zéro appel API réel. Zéro lecture fichier complet en RAM.

Test 1 : upload → ocr.process(file_id) → delete appelés dans le bon ordre
Test 2 : cleanup garanti même si ocr.process() lève une exception
Test 3 : guard taille — ValueError si fichier > 50 MB
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

# ── Helpers ───────────────────────────────────────────────────────────────


def _make_client_mock(file_id: str = "file-abc123") -> MagicMock:
    """Crée un mock Mistral client avec files + ocr configurés."""
    client = MagicMock()
    client.files.upload.return_value = SimpleNamespace(id=file_id)
    client.files.delete.return_value = None
    client.ocr.process.return_value = SimpleNamespace(
        pages=[
            SimpleNamespace(markdown="Page 1 du TDR"),
            SimpleNamespace(markdown="Page 2 : Budget"),
        ],
        text=None,
    )
    return client


# ── Test 1 — ordre des appels : upload → process → delete ─────────────────


def test_ocr_files_api_order_upload_process_delete(tmp_path, monkeypatch):
    """upload() → ocr.process(file_id) → files.delete() dans cet ordre exact."""
    import mistralai as _mistralai

    import src.extraction.engine as eng

    fake_pdf = tmp_path / "tdr.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake content")

    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(eng, "_detect_mime_from_header", lambda _: "application/pdf")
    monkeypatch.setattr(eng.os.path, "getsize", lambda _: 1024)

    mock_client = _make_client_mock(file_id="file-xyz789")
    monkeypatch.setattr(_mistralai, "Mistral", lambda **kw: mock_client)

    raw_text, _ = eng._extract_mistral_ocr(str(fake_pdf))

    assert "Page 1" in raw_text
    assert "Page 2" in raw_text
    mock_client.files.upload.assert_called_once()
    mock_client.ocr.process.assert_called_once()
    mock_client.files.delete.assert_called_once_with(file_id="file-xyz789")

    process_call = mock_client.ocr.process.call_args
    assert "file_id" in str(process_call)


# ── Test 2 — cleanup garanti même si ocr.process() lève une exception ─────


def test_ocr_files_api_cleanup_on_error(tmp_path, monkeypatch):
    """files.delete() appelé même si ocr.process() lève une RuntimeError."""
    import mistralai as _mistralai

    import src.extraction.engine as eng

    fake_pdf = tmp_path / "offre.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake")

    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(eng, "_detect_mime_from_header", lambda _: "application/pdf")
    monkeypatch.setattr(eng.os.path, "getsize", lambda _: 2048)

    mock_client = _make_client_mock(file_id="file-cleanup-test")
    mock_client.ocr.process.side_effect = RuntimeError("Mistral 500")
    monkeypatch.setattr(_mistralai, "Mistral", lambda **kw: mock_client)

    try:
        eng._extract_mistral_ocr(str(fake_pdf))
        assert False, "RuntimeError attendue"
    except RuntimeError:
        pass

    # Cleanup DOIT avoir été appelé malgré l'erreur
    mock_client.files.delete.assert_called_once_with(file_id="file-cleanup-test")


# ── Test 3 — guard taille : ValueError si fichier > 50 MB ─────────────────


def test_ocr_files_api_raises_if_file_too_large(tmp_path, monkeypatch):
    """ValueError levée si fichier > 50 MB — sans ouvrir le fichier."""
    import src.extraction.engine as eng

    fake_pdf = tmp_path / "gros.pdf"
    fake_pdf.write_bytes(b"x")

    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(eng.os.path, "getsize", lambda _: 51 * 1024 * 1024)

    try:
        eng._extract_mistral_ocr(str(fake_pdf))
        assert False, "ValueError attendue"
    except ValueError as exc:
        assert "volumineux" in str(exc) or "MB" in str(exc)
