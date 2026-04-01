"""
Tests Phase 1 — SLA-B dispatch + MIME fix + OCR cascade bridge.

T1 : _dispatch_extraction route SLA-A + SLA-B cloud (incl. alias DB tesseract -> mistral_ocr)
T2 : _dispatch_extraction leve ValueError pour methode inconnue (pas tesseract : alias valide)
T3 : _detect_mime_from_header retourne application/pdf sur magic bytes %PDF
     meme si filetype retourne application/octet-stream
T4 : _detect_mime_from_header fonctionne sans filetype installe
T5 : cascade bridge mock — Mistral OK -> stop
T6 : cascade bridge mock — Mistral echec -> LlamaParse OK
T7 : cascade bridge mock — les deux echouent -> blocked
T8 : cascade bridge — retry sur erreur SSL (1 retry puis succes)
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ── T1 : _dispatch_extraction route les 6 methodes ────────────────────────


def test_dispatch_sla_a_native_pdf(tmp_path, monkeypatch):
    """native_pdf -> _extract_native_pdf."""
    import src.extraction.engine as eng

    fake = tmp_path / "doc.pdf"
    fake.write_bytes(b"%PDF-1.4 BT some text ET")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(eng, "_extract_native_pdf", lambda uri: ("texte natif", {}))

    text, _ = eng._dispatch_extraction({"storage_uri": str(fake)}, "native_pdf")
    assert text == "texte natif"


def test_dispatch_sla_b_mistral_ocr(tmp_path, monkeypatch):
    """mistral_ocr -> _extract_mistral_ocr."""
    import src.extraction.engine as eng

    fake = tmp_path / "scan.pdf"
    fake.write_bytes(b"%PDF-1.4 scan")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(eng, "_extract_mistral_ocr", lambda uri: ("ocr mistral", {}))

    text, _ = eng._dispatch_extraction({"storage_uri": str(fake)}, "mistral_ocr")
    assert text == "ocr mistral"


def test_dispatch_sla_b_tesseract_aliases_mistral_ocr(tmp_path, monkeypatch):
    """Compat DB/API : tesseract -> meme chemin que mistral_ocr (CHECK extraction_jobs.method)."""
    import src.extraction.engine as eng

    fake = tmp_path / "legacy_scan.pdf"
    fake.write_bytes(b"%PDF-1.4 legacy")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(eng, "_extract_mistral_ocr", lambda uri: ("ocr mistral", {}))

    text, _ = eng._dispatch_extraction({"storage_uri": str(fake)}, "tesseract")
    assert text == "ocr mistral"


def test_dispatch_sla_b_llamaparse(tmp_path, monkeypatch):
    """llamaparse -> _extract_llamaparse."""
    import src.extraction.engine as eng

    fake = tmp_path / "llama.pdf"
    fake.write_bytes(b"%PDF-1.4 llama")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(eng, "_extract_llamaparse", lambda uri: ("llama text", {}))

    text, _ = eng._dispatch_extraction({"storage_uri": str(fake)}, "llamaparse")
    assert text == "llama text"


def test_dispatch_sla_b_azure(tmp_path, monkeypatch):
    """azure -> _extract_azure_ocr_fallback."""
    import src.extraction.engine as eng

    fake = tmp_path / "az.pdf"
    fake.write_bytes(b"%PDF-1.4 az")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(
        eng, "_extract_azure_ocr_fallback", lambda uri, mime: ("azure text", {})
    )

    text, _ = eng._dispatch_extraction({"storage_uri": str(fake)}, "azure")
    assert text == "azure text"


# ── T2 : ValueError pour methode inconnue ─────────────────────────────────


def test_dispatch_unknown_method_raises(tmp_path):
    import src.extraction.engine as eng

    with pytest.raises(ValueError) as excinfo:
        eng._dispatch_extraction(
            {"storage_uri": str(tmp_path / "x.pdf")}, "methode_inexistante_xyz"
        )
    assert "inconnue" in str(excinfo.value).lower()


# ── T3 : MIME fix — %PDF magic bytes -> application/pdf ───────────────────


def test_detect_mime_pdf_magic_bytes_overrides_octet_stream(tmp_path, monkeypatch):
    """Quand filetype retourne octet-stream mais magic bytes = %PDF -> application/pdf."""

    fake = tmp_path / "scan.pdf"
    fake.write_bytes(b"%PDF-1.5 fake content")

    # Simuler filetype qui retourne octet-stream (cas proxy/filetype manque)
    class FakeFiletype:
        mime = "application/octet-stream"

    def fake_filetype_guess(header):
        return FakeFiletype()

    import unittest.mock as um

    # filetype est importe lazily (import inside function) — patch sys.modules suffit,
    # pas besoin de importlib.reload (qui mute l'etat global du module).
    with um.patch.dict(
        "sys.modules", {"filetype": um.MagicMock(guess=fake_filetype_guess)}
    ):
        import src.extraction.engine as eng2

        mime = eng2._detect_mime_from_header(str(fake))
        assert mime == "application/pdf", f"Attendu application/pdf, recu {mime}"


def test_detect_mime_pdf_magic_bytes_direct(tmp_path):
    """%PDF magic bytes retournes directement quand filetype plante."""
    import src.extraction.engine as eng

    fake = tmp_path / "direct.pdf"
    fake.write_bytes(b"%PDF-1.4 direct")

    # Patcher filetype pour lever une exception
    import unittest.mock as um

    with um.patch.dict("sys.modules", {"filetype": None}):
        mime = eng._detect_mime_from_header(str(fake))
    # Avec filetype=None -> exception -> fallback magic bytes
    assert mime == "application/pdf"


# ── T4 : MIME retourne application/pdf pour vrai PDF ──────────────────────


def test_detect_mime_real_pdf_bytes(tmp_path):
    """Un fichier avec magic bytes %PDF doit retourner application/pdf."""
    import src.extraction.engine as eng

    fake = tmp_path / "real.pdf"
    fake.write_bytes(b"%PDF-1.4\n%header fake pdf content BT ET")
    mime = eng._detect_mime_from_header(str(fake))
    assert mime == "application/pdf"


# ── T5-T7 : cascade bridge ────────────────────────────────────────────────


def _make_bridge_module():
    """Importe le module bridge depuis scripts/."""
    import importlib.util
    import sys

    bridge_path = (
        Path(__file__).parent.parent / "scripts" / "ingest_to_annotation_bridge.py"
    )
    spec = importlib.util.spec_from_file_location("ingest_bridge", bridge_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ingest_bridge"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_cascade_mistral_ok(tmp_path, monkeypatch):
    """Cascade : Mistral OK -> retour direct, LlamaParse non appele."""
    bridge = _make_bridge_module()

    fake = tmp_path / "scan.pdf"
    fake.write_bytes(b"%PDF-1.4 scan")

    mistral_called = []
    llama_called = []

    def mock_mistral(uri):
        mistral_called.append(uri)
        return "Texte OCR Mistral", {}

    def mock_llama(uri):
        llama_called.append(uri)
        return "Texte LlamaParse", {}

    monkeypatch.setattr(bridge, "_extract_mistral_ocr", mock_mistral)
    monkeypatch.setattr(bridge, "_extract_llamaparse", mock_llama)

    text, route, reason = bridge.extract_with_route(str(fake), "scanned_pdf", "")
    assert text == "Texte OCR Mistral"
    assert route == "mistral_ocr"
    assert reason is None
    assert len(mistral_called) == 1
    assert len(llama_called) == 0


def test_cascade_mistral_fails_llama_ok(tmp_path, monkeypatch):
    """Cascade : Mistral echec -> LlamaParse OK."""
    bridge = _make_bridge_module()

    fake = tmp_path / "scan2.pdf"
    fake.write_bytes(b"%PDF-1.4 scan2")

    def mock_mistral(uri):
        raise RuntimeError("Mistral API error")

    def mock_llama(uri):
        return "Texte LlamaParse", {}

    monkeypatch.setattr(bridge, "_extract_mistral_ocr", mock_mistral)
    monkeypatch.setattr(bridge, "_extract_llamaparse", mock_llama)

    text, route, reason = bridge.extract_with_route(str(fake), "scanned_pdf", "")
    assert text == "Texte LlamaParse"
    assert route == "llamaparse"
    assert reason is None


def test_cascade_both_fail_blocked(tmp_path, monkeypatch):
    """Cascade : Mistral + LlamaParse echouent -> blocked."""
    bridge = _make_bridge_module()

    fake = tmp_path / "scan3.pdf"
    fake.write_bytes(b"%PDF-1.4 scan3")

    def mock_mistral(uri):
        raise RuntimeError("Mistral down")

    def mock_llama(uri):
        raise RuntimeError("Llama down")

    monkeypatch.setattr(bridge, "_extract_mistral_ocr", mock_mistral)
    monkeypatch.setattr(bridge, "_extract_llamaparse", mock_llama)

    text, route, reason = bridge.extract_with_route(str(fake), "scanned_pdf", "")
    assert text == ""
    assert route == "blocked"
    assert reason == "no_text_all_extractors"


# ── T8 : retry SSL ────────────────────────────────────────────────────────


def test_cascade_ssl_retry_then_success(tmp_path, monkeypatch):
    """Retry sur erreur SSL : echec tentative 1 (SSL) -> succes tentative 2."""
    bridge = _make_bridge_module()

    fake = tmp_path / "ssl_scan.pdf"
    fake.write_bytes(b"%PDF-1.4 ssl_scan")

    attempts = []

    def mock_mistral(uri):
        attempts.append(len(attempts) + 1)
        if len(attempts) == 1:
            raise OSError("CERTIFICATE_VERIFY_FAILED: SSL handshake failed")
        return "Texte apres retry", {}

    monkeypatch.setattr(bridge, "_extract_mistral_ocr", mock_mistral)
    monkeypatch.setattr(bridge, "_extract_llamaparse", lambda uri: ("llama", {}))

    # Patcher sleep pour ne pas attendre
    import unittest.mock as um

    with um.patch("time.sleep"):
        text, route, reason = bridge.extract_with_route(str(fake), "scanned_pdf", "")

    assert text == "Texte apres retry"
    assert route == "mistral_ocr"
    assert len(attempts) == 2


# ── _retry_cloud_ocr unit tests ───────────────────────────────────────────


def test_retry_cloud_ocr_three_strikes_raises(monkeypatch):
    """Après 3 échecs réseau, _retry_cloud_ocr relève la dernière exception."""
    import src.extraction.engine as eng

    calls = []

    def flaky_func(_uri):
        calls.append(1)
        raise ConnectionError("network failure")

    monkeypatch.setattr(eng._BACKOFF_WAITER, "wait", lambda _t: None)
    with pytest.raises(ConnectionError, match="network failure"):
        eng._retry_cloud_ocr(flaky_func, "/fake/path.pdf", "test_ocr")
    assert len(calls) == eng._OCR_MAX_RETRIES


def test_retry_cloud_ocr_non_retryable_raises_immediately(monkeypatch):
    """ValueError (non-retryable) est propagée sans retry."""
    import src.extraction.engine as eng

    calls = []

    def fatal_func(_uri):
        calls.append(1)
        raise ValueError("bad params — non retryable")

    monkeypatch.setattr(eng._BACKOFF_WAITER, "wait", lambda _t: None)
    with pytest.raises(ValueError, match="non retryable"):
        eng._retry_cloud_ocr(fatal_func, "/fake/path.pdf", "test_ocr")
    assert len(calls) == 1, "Non-retryable doit échouer au 1er essai sans retry"


def test_retry_cloud_ocr_success_first_attempt(monkeypatch):
    """Succès au premier essai — aucun retry, résultat retourné."""
    import src.extraction.engine as eng

    wait_calls = []
    monkeypatch.setattr(eng._BACKOFF_WAITER, "wait", lambda _t: wait_calls.append(1))

    def ok_func(_uri):
        return ("extracted text", {})

    text, _ = eng._retry_cloud_ocr(ok_func, "/fake/path.pdf", "test_ocr")
    assert text == "extracted text"
    assert not wait_calls, "Aucun wait si succès immédiat"


def test_retry_cloud_ocr_api_key_missing_raises_immediately(monkeypatch):
    """APIKeyMissingError (non-retryable) est propagée sans retry."""
    import src.extraction.engine as eng

    # Même objet classe que _retry_cloud_ocr (évite doublons d'import sous pytest-cov).
    api_key_missing_cls = eng._NON_RETRYABLE_EXCEPTIONS[0]

    calls = []

    def missing_key_func(_uri):
        calls.append(1)
        raise api_key_missing_cls("MISTRAL_API_KEY absent")

    monkeypatch.setattr(eng._BACKOFF_WAITER, "wait", lambda _t: None)
    with pytest.raises(api_key_missing_cls, match="MISTRAL_API_KEY"):
        eng._retry_cloud_ocr(missing_key_func, "/fake/path.pdf", "test_ocr")
    assert len(calls) == 1, "APIKeyMissingError doit échouer immédiatement sans retry"


def test_retry_cloud_ocr_azure_config_error_raises_immediately(monkeypatch):
    """_OcrConfigError (Azure non configuré) est non-retryable."""
    import src.extraction.engine as eng

    calls = []

    def azure_config_missing(_uri):
        calls.append(1)
        raise eng._OcrConfigError("Azure endpoint manquant")

    monkeypatch.setattr(eng._BACKOFF_WAITER, "wait", lambda _t: None)
    with pytest.raises(eng._OcrConfigError, match="Azure endpoint manquant"):
        eng._retry_cloud_ocr(azure_config_missing, "/fake/path.pdf", "azure")
    assert len(calls) == 1, "_OcrConfigError doit échouer immédiatement sans retry"
