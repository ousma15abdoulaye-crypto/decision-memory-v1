"""
Test : Validation magic bytes upload
Gate : 🔴 BLOQUANT CI (actif dès M-DOCS-CORE)
ADR  : ADR-0002 §6.2
INV  : Sécurité upload — Constitution §5.5
"""
import pytest


@pytest.mark.skip(
    reason="À implémenter dans M-DOCS-CORE. "
           "Ce test valide que l'upload rejette les fichiers "
           "non autorisés par magic bytes (pas Content-Type header). "
           "Retirer le skip et implémenter quand M-DOCS-CORE est actif."
)
def test_upload_rejects_executable_by_magic_bytes():
    """
    Vérifier que l'upload rejette un fichier .exe déguisé en .pdf
    par analyse des magic bytes réels (python-magic).
    🔴 BLOQUE CI quand actif.
    """
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-DOCS-CORE."
)
def test_upload_accepts_valid_pdf():
    """Vérifier qu'un PDF valide est accepté."""
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-DOCS-CORE."
)
def test_upload_accepts_valid_xlsx():
    """Vérifier qu'un XLSX valide est accepté."""
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-DOCS-CORE."
)
def test_upload_accepts_valid_docx():
    """Vérifier qu'un DOCX valide est accepté."""
    pass


@pytest.mark.skip(
    reason="À implémenter dans M-DOCS-CORE."
)
def test_upload_rejects_blocked_extension():
    """Vérifier que .sh, .py, .exe, .bat sont rejetés."""
    pass
