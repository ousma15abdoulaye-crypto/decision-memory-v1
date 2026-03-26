"""
Annotation pipeline passes (Pass 0, 0.5, 1, …).

Implementations are added incrementally per ANNOTATION_BACKEND_MIGRATION_STRATEGY.md.
Contracts: docs/contracts/annotation/
"""

from src.annotation.passes.pass_0_5_quality_gate import run_pass_0_5_quality_gate
from src.annotation.passes.pass_0_ingestion import run_pass_0_ingestion
from src.annotation.passes.pass_1_router import run_pass_1_router

__all__ = [
    "run_pass_0_ingestion",
    "run_pass_0_5_quality_gate",
    "run_pass_1_router",
]
