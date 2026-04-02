"""OCDS — expose build_default pour tests."""

from __future__ import annotations

from src.procurement.compliance_models_m13 import OCDSProcessCoverage


def build_ocds_default() -> OCDSProcessCoverage:
    return OCDSProcessCoverage.build_default()
