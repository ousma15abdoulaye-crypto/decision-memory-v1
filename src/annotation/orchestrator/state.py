"""
FSM states, feature flags, and constants for the annotation pipeline orchestrator.

Spec : docs/contracts/annotation/ANNOTATION_ORCHESTRATOR_FSM.md
"""

from __future__ import annotations

import os
from enum import StrEnum

ENV_USE_ORCHESTRATOR = "ANNOTATION_USE_PASS_ORCHESTRATOR"
ENV_USE_M12_SUBPASSES = "ANNOTATION_USE_M12_SUBPASSES"
ENV_USE_PASS_2A = "ANNOTATION_USE_PASS_2A"

_DEFAULT_MAX_ATTEMPTS = 2


def use_pass_orchestrator() -> bool:
    return os.environ.get(ENV_USE_ORCHESTRATOR, "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def use_m12_subpasses() -> bool:
    """Feature flag: when enabled, run_passes_0_to_1 chains 1A-1D instead of pass_1_router."""
    return os.environ.get(ENV_USE_M12_SUBPASSES, "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def use_pass_2a() -> bool:
    """Feature flag: after Pass 1D, run M13 Pass 2A (regulatory profile)."""
    return os.environ.get(ENV_USE_PASS_2A, "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


class AnnotationPipelineState(StrEnum):
    INGESTED = "ingested"
    PASS_0_DONE = "pass_0_done"
    QUALITY_ASSESSED = "quality_assessed"
    ROUTED = "routed"
    PASS_1A_DONE = "pass_1a_done"
    PASS_1B_DONE = "pass_1b_done"
    PASS_1C_DONE = "pass_1c_done"
    PASS_1D_DONE = "pass_1d_done"
    PASS_2A_DONE = "pass_2a_done"
    LLM_PREANNOTATION_PENDING = "llm_preannotation_pending"
    LLM_PREANNOTATION_DONE = "llm_preannotation_done"
    VALIDATED = "validated"
    REVIEW_REQUIRED = "review_required"
    ANNOTATED_VALIDATED = "annotated_validated"
    REJECTED = "rejected"
    DEAD_LETTER = "dead_letter"


TERMINAL_STATES: frozenset[AnnotationPipelineState] = frozenset(
    {
        AnnotationPipelineState.PASS_1D_DONE,
        AnnotationPipelineState.PASS_2A_DONE,
        AnnotationPipelineState.DEAD_LETTER,
        AnnotationPipelineState.REVIEW_REQUIRED,
        AnnotationPipelineState.REJECTED,
        AnnotationPipelineState.ROUTED,
        AnnotationPipelineState.LLM_PREANNOTATION_PENDING,
        AnnotationPipelineState.LLM_PREANNOTATION_DONE,
        AnnotationPipelineState.VALIDATED,
        AnnotationPipelineState.ANNOTATED_VALIDATED,
    }
)

M12_RESUMABLE_STATES: frozenset[AnnotationPipelineState] = frozenset(
    {
        AnnotationPipelineState.QUALITY_ASSESSED,
        AnnotationPipelineState.PASS_1A_DONE,
        AnnotationPipelineState.PASS_1B_DONE,
        AnnotationPipelineState.PASS_1C_DONE,
    }
)

M12_STATE_ORDER: list[AnnotationPipelineState] = [
    AnnotationPipelineState.QUALITY_ASSESSED,
    AnnotationPipelineState.PASS_1A_DONE,
    AnnotationPipelineState.PASS_1B_DONE,
    AnnotationPipelineState.PASS_1C_DONE,
    AnnotationPipelineState.PASS_1D_DONE,
    AnnotationPipelineState.PASS_2A_DONE,
]


def m12_run_terminal(state: AnnotationPipelineState) -> bool:
    """Terminal pour une exécution M12 (1A–1D–[2A])."""
    if state == AnnotationPipelineState.PASS_2A_DONE:
        return True
    if state == AnnotationPipelineState.PASS_1D_DONE:
        return not use_pass_2a()
    return state in TERMINAL_STATES
