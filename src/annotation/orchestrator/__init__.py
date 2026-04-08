"""
Orchestrateur FSM — pipeline d'annotation multipasses.

Package decomposed from the original orchestrator.py monolith.
Re-exports all public symbols for backward compatibility.
"""

from .orchestrator import AnnotationOrchestrator, default_pipeline_runs_dir
from .records import PipelineRunRecord, TransitionLogEntry
from .state import (
    AnnotationPipelineState,
    use_m12_subpasses,
    use_pass_2a,
    use_pass_orchestrator,
)

__all__ = [
    "AnnotationOrchestrator",
    "AnnotationPipelineState",
    "PipelineRunRecord",
    "TransitionLogEntry",
    "default_pipeline_runs_dir",
    "use_m12_subpasses",
    "use_pass_2a",
    "use_pass_orchestrator",
]
