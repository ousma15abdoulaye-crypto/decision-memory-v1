"""
Test : SLA Classe B — OCR via queue, sans blocage
Gate : 🔴 BLOQUANT CI (actif dès M-PIPELINE-A-E2E)
ADR  : ADR-0002 §2.5
REF  : §6.2 Constitution V3.3.2
"""

import pytest


@pytest.mark.skip(
    reason="À implémenter dans M-PIPELINE-A-E2E. "
    "Vérifier que l'OCR est mis en queue asynchrone "
    "et ne bloque pas l'app. "
    "🔴 BLOQUE CI si non respecté."
)
def test_ocr_scan_is_queued_not_synchronous(scan_document_fixture):
    """
    L'upload d'un scan OCR doit retourner immédiatement
    avec status 'pending' ou 'processing'.
    L'OCR ne doit pas bloquer le thread principal.
    """
    pass


@pytest.mark.skip(reason="À implémenter dans M-PIPELINE-A-E2E.")
def test_ocr_does_not_block_native_pdf_processing():
    """
    Un scan OCR en cours ne doit pas bloquer
    le traitement d'un PDF natif simultané.
    SLA-A toujours respecté même avec OCR en cours.
    """
    pass
