# src/couche_a/pipeline/__init__.py
"""
Pipeline A — Couche A uniquement.
ADR-0012 : orchestrateur d'exécution, zéro Couche B, zéro export CBA/PV.
"""

from .models import (
    CaseAnalysisSnapshot,
    PipelineResult,
    PipelineStepName,
    StepOutcome,
)
from .service import run_pipeline_a_partial

__all__ = [
    "CaseAnalysisSnapshot",
    "PipelineResult",
    "PipelineStepName",
    "StepOutcome",
    "run_pipeline_a_partial",
]
