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
from .service import run_pipeline_a_e2e, run_pipeline_a_partial
from .service_utils import get_last_pipeline_run

__all__ = [
    "CaseAnalysisSnapshot",
    "PipelineResult",
    "PipelineStepName",
    "StepOutcome",
    "get_last_pipeline_run",
    "run_pipeline_a_e2e",
    "run_pipeline_a_partial",
]
