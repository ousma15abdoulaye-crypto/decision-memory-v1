# tests/pipeline/test_pipeline_a_partial_statuses.py
"""
L10 — Statuts pipeline A/partial.

Prouve :
  preflight blocked → PipelineResult.status == 'blocked'
  PipelineResult typé Pydantic même en blocked
  blocked en preflight → steps = [preflight] uniquement
  exception dans un step → _safe_step capture → failed structuré (pas propagation brute)
  duration_ms >= 0 sur steps et run
  status != 'complete' dans #10
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

from src.couche_a.pipeline.models import PipelineResult, StepOutcome
from src.couche_a.pipeline.service import (
    RC_CASE_NOT_FOUND,
    _safe_step,
    run_pipeline_a_partial,
)

# ---------------------------------------------------------------------------
# preflight blocked → PipelineResult.status == 'blocked'
# ---------------------------------------------------------------------------


def test_pipeline_status_blocked_when_preflight_blocked(db_conn):
    """Case inexistant → PipelineResult.status == 'blocked'."""
    case_id = f"ghost-{uuid.uuid4()}"
    result = run_pipeline_a_partial(
        case_id=case_id, triggered_by="test-runner", conn=db_conn
    )

    assert result.status == "blocked", f"Attendu blocked, obtenu {result.status!r}"


# ---------------------------------------------------------------------------
# PipelineResult est typé Pydantic même en blocked
# ---------------------------------------------------------------------------


def test_pipeline_result_is_typed_even_when_blocked(db_conn):
    """PipelineResult est une instance Pydantic valide même en cas de blocked."""
    case_id = f"ghost-{uuid.uuid4()}"
    result = run_pipeline_a_partial(
        case_id=case_id, triggered_by="test-runner", conn=db_conn
    )

    assert isinstance(
        result, PipelineResult
    ), f"Attendu PipelineResult, obtenu {type(result)}"
    assert result.case_id == case_id
    assert result.triggered_by == "test-runner"


# ---------------------------------------------------------------------------
# blocked en preflight → steps = [preflight] uniquement
# ---------------------------------------------------------------------------


def test_pipeline_blocked_contains_only_preflight_step(db_conn):
    """preflight blocked → steps contient uniquement le step 'preflight'."""
    case_id = f"ghost-{uuid.uuid4()}"
    result = run_pipeline_a_partial(
        case_id=case_id, triggered_by="test-runner", conn=db_conn
    )

    assert len(result.steps) == 1, (
        f"Attendu 1 step, obtenu {len(result.steps)}: "
        f"{[s.step_name for s in result.steps]}"
    )
    assert result.steps[0].step_name == "preflight"
    assert result.steps[0].status == "blocked"
    assert result.steps[0].reason_code == RC_CASE_NOT_FOUND


# ---------------------------------------------------------------------------
# exception dans un step → _safe_step capture → failed structuré
# ---------------------------------------------------------------------------


def test_safe_step_captures_exception_as_failed():
    """_safe_step capture toute exception et retourne StepOutcome(failed)."""

    def _raises():
        raise RuntimeError("Erreur simulée pour test")

    outcome = _safe_step("test_step", _raises)

    assert isinstance(
        outcome, StepOutcome
    ), f"Attendu StepOutcome, obtenu {type(outcome)}"
    assert outcome.status == "failed"
    assert outcome.reason_code == "STEP_EXCEPTION"
    assert "Erreur simulée" in (outcome.reason_message or "")


# ---------------------------------------------------------------------------
# duration_ms >= 0 sur steps et run
# ---------------------------------------------------------------------------


def test_pipeline_duration_ms_non_negative(db_conn):
    """duration_ms >= 0 sur run et chaque step (INV-P12)."""
    case_id = f"ghost-{uuid.uuid4()}"
    result = run_pipeline_a_partial(
        case_id=case_id, triggered_by="test-runner", conn=db_conn
    )

    assert (
        result.duration_ms >= 0
    ), f"run.duration_ms doit être >= 0, obtenu {result.duration_ms}"
    for step in result.steps:
        assert step.duration_ms >= 0, (
            f"step.duration_ms doit être >= 0 pour {step.step_name}, "
            f"obtenu {step.duration_ms}"
        )


# ---------------------------------------------------------------------------
# status != 'complete' dans #10
# ---------------------------------------------------------------------------


def test_pipeline_status_never_complete(db_conn, pipeline_case_with_dao_and_offers):
    """PipelineResult.status != 'complete' (interdit dans #10, réservé #14)."""
    case_id = pipeline_case_with_dao_and_offers
    result = run_pipeline_a_partial(
        case_id=case_id, triggered_by="test-runner", conn=db_conn
    )

    assert (
        result.status != "complete"
    ), f"status='complete' est interdit dans #10 — obtenu {result.status!r}"


# ---------------------------------------------------------------------------
# Stabilité : step exception → pipeline fails structuralement
# ---------------------------------------------------------------------------


def test_pipeline_step_exception_produces_failed_step(
    db_conn, pipeline_case_with_dao_and_offers
):
    """
    Si un step lève une exception inattendue, _safe_step la capture
    et le step est marqué 'failed' — pas de propagation brute.
    Test déterministe via patch ciblé sur extraction_summary.
    pipeline_case_with_dao_and_offers assure que preflight passe.
    """
    case_id = pipeline_case_with_dao_and_offers

    with patch(
        "src.couche_a.pipeline.service._load_extraction_summary",
        side_effect=RuntimeError("extraction intentionnellement cassée"),
    ):
        result = run_pipeline_a_partial(
            case_id=case_id, triggered_by="test-patch", conn=db_conn
        )

    extraction_steps = [s for s in result.steps if s.step_name == "extraction_summary"]

    assert (
        extraction_steps
    ), "Le step extraction_summary doit être présent même si exception"

    extraction_step = extraction_steps[0]
    assert (
        extraction_step.status == "failed"
    ), f"step extraction_summary doit être failed, obtenu {extraction_step.status!r}"
    assert extraction_step.reason_code == "STEP_EXCEPTION"
    assert result.status != "complete"
