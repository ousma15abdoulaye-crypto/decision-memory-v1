"""
Data classes for annotation pipeline run records and transition logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.annotation.pass_output import AnnotationPassOutput


@dataclass
class TransitionLogEntry:
    run_id: str
    document_id: str
    from_state: str
    to_state: str
    pass_name: str
    duration_ms: int
    status: str
    error_codes: list[str] = field(default_factory=list)


@dataclass
class PipelineRunRecord:
    run_id: str
    document_id: str
    state: str
    pass_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    transition_log: list[dict[str, Any]] = field(default_factory=list)


def serialize_pass_output(out: AnnotationPassOutput) -> dict[str, Any]:
    return out.model_dump(mode="json")
