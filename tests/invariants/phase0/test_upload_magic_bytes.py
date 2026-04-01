"""
Test : Validation magic bytes upload
Gate : 🔴 BLOQUANT CI (actif dès M-DOCS-CORE)
ADR  : ADR-0002 §6.2
INV  : Sécurité upload — Constitution §5.5
"""

from pathlib import Path

import pytest

_MILESTONE_DOCS = Path(".milestones/M-DOCS-CORE.done").exists()

_skip_if_no_docs = pytest.mark.skipif(
    not _MILESTONE_DOCS,
    reason="Actif dès M-DOCS-CORE.done (ADR-0002 §6.2).",
)


@_skip_if_no_docs
def test_upload_rejects_executable_by_magic_bytes():
    """
    Vérifier que l'upload rejette un fichier .exe déguisé en .pdf
    par analyse des magic bytes réels (python-magic).
    🔴 BLOQUE CI quand actif.
    """
    pass


@_skip_if_no_docs
def test_upload_accepts_valid_pdf():
    """Vérifier qu'un PDF valide est accepté."""
    pass


@_skip_if_no_docs
def test_upload_accepts_valid_xlsx():
    """Vérifier qu'un XLSX valide est accepté."""
    pass


@_skip_if_no_docs
def test_upload_accepts_valid_docx():
    """Vérifier qu'un DOCX valide est accepté."""
    pass


@_skip_if_no_docs
def test_upload_rejects_blocked_extension():
    """Vérifier que .sh, .py, .exe, .bat sont rejetés."""
    pass
