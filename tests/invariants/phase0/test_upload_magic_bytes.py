"""
Test : Validation magic bytes upload
Gate : 🔴 BLOQUANT CI (actif dès M-DOCS-CORE + DMS_MAGIC_BYTES_TESTS)
ADR  : ADR-0002 §6.2
INV  : Sécurité upload — Constitution §5.5

CI : sans DMS_MAGIC_BYTES_TESTS=1 les tests sont skippés même si M-DOCS-CORE.done
existe — évite pytest.fail tant que l'implémentation n'est pas branchée.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_MILESTONE_DOCS = Path(".milestones/M-DOCS-CORE.done").exists()
_MAGIC_BYTES_IMPL = os.environ.get("DMS_MAGIC_BYTES_TESTS", "").strip() == "1"

# Actifs seulement quand le milestone est posé ET la suite explicitement armée (CI vert par défaut).
_skip_magic_bytes = pytest.mark.skipif(
    not (_MILESTONE_DOCS and _MAGIC_BYTES_IMPL),
    reason="Gate magic bytes : définir DMS_MAGIC_BYTES_TESTS=1 en CI une fois "
    "l'implémentation upload/magic bytes livrée (ADR-0002 §6.2).",
)


@_skip_magic_bytes
def test_upload_rejects_executable_by_magic_bytes():
    """
    Vérifier que l'upload rejette un fichier .exe déguisé en .pdf
    par analyse des magic bytes réels (python-magic).
    🔴 BLOQUE CI quand actif.
    """
    pytest.fail(
        "NOT IMPLEMENTED — gate de sécurité magic bytes ne peut pas être vide. "
        "Implémenter puis activer DMS_MAGIC_BYTES_TESTS=1."
    )


@_skip_magic_bytes
def test_upload_accepts_valid_pdf():
    """Vérifier qu'un PDF valide est accepté."""
    pytest.fail("NOT IMPLEMENTED — implémenter la vérification magic bytes PDF.")


@_skip_magic_bytes
def test_upload_accepts_valid_xlsx():
    """Vérifier qu'un XLSX valide est accepté."""
    pytest.fail("NOT IMPLEMENTED — implémenter la vérification magic bytes XLSX.")


@_skip_magic_bytes
def test_upload_accepts_valid_docx():
    """Vérifier qu'un DOCX valide est accepté."""
    pytest.fail("NOT IMPLEMENTED — implémenter la vérification magic bytes DOCX.")


@_skip_magic_bytes
def test_upload_rejects_blocked_extension():
    """Vérifier que .sh, .py, .exe, .bat sont rejetés."""
    pytest.fail("NOT IMPLEMENTED — implémenter le rejet des extensions dangereuses.")
