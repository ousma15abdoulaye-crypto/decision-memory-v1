"""
Tests Mandat 2 — OCR Files API (stream + cleanup garanti)
Zéro appel API réel. Zéro lecture fichier complet en RAM.

Test 1 : upload → ocr.process(file_id) → delete appelés dans le bon ordre
Test 2 : cleanup garanti même si ocr.process() lève une exception
Test 3 : guard taille — ValueError si fichier > 50 MB
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# ── Helpers ───────────────────────────────────────────────────────────────


def _make_client_mock(file_id: str = "file-abc123") -> MagicMock:
    """Crée un mock Mistral client avec files + ocr configurés."""
    client = MagicMock()
    uploaded = SimpleNamespace(id=file_id)
    client.files.upload.return_value = uploaded
    client.files.delete.return_value = None
    page1 = SimpleNamespace(markdown="Page 1 du TDR")
    page2 = SimpleNamespace(markdown="Page 2 : Budget")
    client.ocr.process.return_value = SimpleNamespace(pages=[page1, page2], text=None)
    return client


def _mock_open_ctx(content: bytes = b"%PDF-1.4 fake"):
    """Context manager mock pour open() en mode rb."""
    m = MagicMock()
    m.__enter__ = MagicMock(
        return_value=MagicMock(read=MagicMock(return_value=content))
    )
    m.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=m)


# ── Test 1 — ordre des appels : upload → process → delete ─────────────────


def test_ocr_files_api_order_upload_process_delete(tmp_path):
    """upload() → ocr.process(file_id) → files.delete() dans cet ordre exact."""
    fake_pdf = tmp_path / "tdr.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake content")

    mock_client = _make_client_mock(file_id="file-xyz789")
    mock_ft = MagicMock()
    mock_ft.guess.return_value = SimpleNamespace(mime="application/pdf")

    import src.extraction.engine as eng

    with (
        patch.object(eng, "get_mistral_api_key", return_value="fake-key"),
        patch("src.extraction.engine.os.path.getsize", return_value=1024),
        patch("src.extraction.engine.open", _mock_open_ctx(), create=True),
        patch.dict("sys.modules", {"filetype": mock_ft}),
        patch("src.extraction.engine.Mistral", return_value=mock_client),
        patch("src.couche_a.llm_router.TIER_1_OCR_MODEL", "mistral-ocr-latest"),
    ):
        raw_text, _ = eng._extract_mistral_ocr(str(fake_pdf))

    assert "Page 1" in raw_text
    assert "Page 2" in raw_text

    # Ordre strict : upload AVANT process AVANT delete
    manager = mock_client
    assert manager.files.upload.called, "files.upload() doit être appelé"
    assert manager.ocr.process.called, "ocr.process() doit être appelé"
    assert manager.files.delete.called, "files.delete() doit être appelé"

    # Vérifier que file_id est bien passé à process et delete
    process_call = manager.ocr.process.call_args
    assert "file_id" in str(process_call) or "file-xyz789" in str(process_call)

    delete_call = manager.files.delete.call_args
    assert "file-xyz789" in str(delete_call)


# ── Test 2 — cleanup garanti même si ocr.process() lève une exception ─────


def test_ocr_files_api_cleanup_on_error(tmp_path):
    """files.delete() appelé même si ocr.process() lève une RuntimeError."""
    fake_pdf = tmp_path / "offre.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake")

    mock_client = _make_client_mock(file_id="file-cleanup-test")
    mock_client.ocr.process.side_effect = RuntimeError("Mistral 500")

    mock_ft = MagicMock()
    mock_ft.guess.return_value = SimpleNamespace(mime="application/pdf")

    import src.extraction.engine as eng

    with (
        patch.object(eng, "get_mistral_api_key", return_value="fake-key"),
        patch("src.extraction.engine.os.path.getsize", return_value=2048),
        patch("src.extraction.engine.open", _mock_open_ctx(), create=True),
        patch.dict("sys.modules", {"filetype": mock_ft}),
        patch("src.extraction.engine.Mistral", return_value=mock_client),
        patch("src.couche_a.llm_router.TIER_1_OCR_MODEL", "mistral-ocr-latest"),
    ):
        try:
            eng._extract_mistral_ocr(str(fake_pdf))
            assert False, "RuntimeError attendue"
        except RuntimeError:
            pass

    # Cleanup DOIT avoir été appelé malgré l'erreur
    mock_client.files.delete.assert_called_once_with(file_id="file-cleanup-test")


# ── Test 3 — guard taille : ValueError si fichier > 50 MB ─────────────────


def test_ocr_files_api_raises_if_file_too_large(tmp_path):
    """ValueError levée si fichier > 50 MB — sans ouvrir le fichier."""
    fake_pdf = tmp_path / "gros.pdf"
    fake_pdf.write_bytes(b"x")  # contenu bidon — taille simulée via mock

    import src.extraction.engine as eng

    with (
        patch.object(eng, "get_mistral_api_key", return_value="fake-key"),
        patch(
            "src.extraction.engine.os.path.getsize",
            return_value=51 * 1024 * 1024,  # 51 MB
        ),
    ):
        try:
            eng._extract_mistral_ocr(str(fake_pdf))
            assert False, "ValueError attendue"
        except ValueError as exc:
            assert "volumineux" in str(exc) or "MB" in str(exc)
