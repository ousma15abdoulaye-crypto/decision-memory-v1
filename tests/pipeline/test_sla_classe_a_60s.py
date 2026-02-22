"""
Test : SLA Classe A — PDF natifs/XLSX/DOCX < 60s
Gate : 🔴 BLOQUANT CI (actif dès M-PIPELINE-A-E2E)
ADR  : ADR-0002 §2.5
REF  : §6.2 Constitution V3.3.2
"""

import time

import pytest


@pytest.mark.slow
@pytest.mark.skip(
    reason="À implémenter dans M-PIPELINE-A-E2E. "
    "Fixture réaliste requise : 20+ fournisseurs, 10+ lots. "
    "SLA-A : PDF natifs / XLSX / DOCX → < 60 secondes. "
    "🔴 BLOQUE CI si dépassement."
)
def test_pipeline_a_sla_classe_a_under_60s(realistic_case_20_suppliers):
    """
    Pipeline Couche A complet sur documents natifs
    doit s'exécuter en moins de 60 secondes.
    SLA-A Constitution §6.2.
    🔴 BLOQUE CI si dépassement.
    """
    start = time.monotonic()
    # result = run_pipeline_a(realistic_case_20_suppliers.id)
    elapsed = time.monotonic() - start

    assert elapsed < 60.0, (
        f"SLA-A violé : {elapsed:.2f}s > 60s. Optimiser extraction ou réduire scope."
    )
