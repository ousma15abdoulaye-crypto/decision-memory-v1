# src/couche_a/pipeline/service.py
"""
Orchestrateur Pipeline A — Couche A uniquement (ADR-0012).

Séquence : preflight → extraction_summary → criteria_summary
           → normalization_summary → scoring → build CAS v1 → persist atomique.
"""

from __future__ import annotations

import uuid
from typing import Any

from .cas_builder import build_case_analysis_snapshot, load_case_row
from .models import PipelineResult, PipelineStepResult
from .service_utils import (
    _duration_ms,
    _now,
    _safe_step,
    _to_step_result,
    persist_pipeline_run_and_steps,
)
from .steps import (
    load_criteria_summary,
    load_extraction_summary,
    load_normalization_summary,
    preflight_case_a_partial,
    run_scoring_step,
)

# Re-export for backward compatibility
_preflight_case_a_partial = preflight_case_a_partial
_load_extraction_summary = load_extraction_summary
_load_criteria_summary = load_criteria_summary
_load_normalization_summary = load_normalization_summary
_run_scoring_step = run_scoring_step


def run_pipeline_a_partial(
    case_id: str,
    triggered_by: str,
    conn: Any,
) -> PipelineResult:
    """
    Orchestre l'exécution du pipeline A (mode partial).

    Statuts possibles : blocked | incomplete | failed | partial_complete.
    """
    run_id = str(uuid.uuid4())
    started_at = _now()
    steps: list[PipelineStepResult] = []

    pf_start = _now()
    pf_outcome = _safe_step("preflight", preflight_case_a_partial, case_id, conn)
    steps.append(_to_step_result("preflight", pf_outcome, pf_start))

    if pf_outcome.status == "blocked":
        finished_at = _now()
        dur = _duration_ms(started_at, finished_at)
        persist_pipeline_run_and_steps(
            conn,
            run_id,
            case_id,
            triggered_by,
            "blocked",
            started_at,
            finished_at,
            dur,
            steps,
            None,
        )
        return PipelineResult(
            run_id=run_id,
            case_id=case_id,
            status="blocked",
            steps=steps,
            cas=None,
            triggered_by=triggered_by,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=dur,
            errors=[pf_outcome.reason_message or pf_outcome.reason_code or "blocked"],
        )

    case_row = load_case_row(case_id, conn) or {}

    ex_start = _now()
    ex_outcome = _safe_step(
        "extraction_summary", load_extraction_summary, case_id, conn
    )
    steps.append(_to_step_result("extraction_summary", ex_outcome, ex_start))

    cr_start = _now()
    cr_outcome = _safe_step("criteria_summary", load_criteria_summary, case_id, conn)
    steps.append(_to_step_result("criteria_summary", cr_outcome, cr_start))

    nr_start = _now()
    nr_outcome = _safe_step(
        "normalization_summary", load_normalization_summary, case_id, conn
    )
    steps.append(_to_step_result("normalization_summary", nr_outcome, nr_start))

    sc_start = _now()
    sc_outcome = _safe_step("scoring", run_scoring_step, case_id, conn)
    steps.append(_to_step_result("scoring", sc_outcome, sc_start))

    cas = build_case_analysis_snapshot(case_id, steps, case_row)

    step_statuses = {s.status for s in steps}
    if "failed" in step_statuses:
        pipeline_status = "failed"
    elif "blocked" in step_statuses or "incomplete" in step_statuses:
        pipeline_status = "incomplete"
    else:
        pipeline_status = "partial_complete"

    finished_at = _now()
    dur = _duration_ms(started_at, finished_at)

    persist_pipeline_run_and_steps(
        conn,
        run_id,
        case_id,
        triggered_by,
        pipeline_status,
        started_at,
        finished_at,
        dur,
        steps,
        cas,
    )

    errors: list[str] = [
        s.reason_message or s.reason_code or ""
        for s in steps
        if s.status in ("failed", "blocked", "incomplete") and s.reason_code
    ]

    return PipelineResult(
        run_id=run_id,
        case_id=case_id,
        status=pipeline_status,
        steps=steps,
        cas=cas,
        triggered_by=triggered_by,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=dur,
        errors=errors,
    )


def run_pipeline_a_e2e(
    case_id: str,
    triggered_by: str,
    conn: Any,
    force_recompute: bool = False,
) -> PipelineResult:
    """
    Orchestre l'exécution du pipeline A en mode e2e.

    INV-P16 (strict) : tout step 'incomplete' → statut global 'incomplete'.
    """
    run_id = str(uuid.uuid4())
    started_at = _now()
    steps: list[PipelineStepResult] = []

    pf_start = _now()
    pf_outcome = _safe_step("preflight", preflight_case_a_partial, case_id, conn)
    steps.append(_to_step_result("preflight", pf_outcome, pf_start))

    if pf_outcome.status == "blocked":
        finished_at = _now()
        dur = _duration_ms(started_at, finished_at)
        persist_pipeline_run_and_steps(
            conn,
            run_id,
            case_id,
            triggered_by,
            "blocked",
            started_at,
            finished_at,
            dur,
            steps,
            None,
            force_recompute=force_recompute,
            mode="e2e",
        )
        return PipelineResult(
            run_id=run_id,
            case_id=case_id,
            status="blocked",
            mode="e2e",
            force_recompute=force_recompute,
            steps=steps,
            cas=None,
            triggered_by=triggered_by,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=dur,
            errors=[pf_outcome.reason_message or pf_outcome.reason_code or "blocked"],
        )

    case_row = load_case_row(case_id, conn) or {}

    ex_start = _now()
    ex_outcome = _safe_step(
        "extraction_summary", load_extraction_summary, case_id, conn
    )
    steps.append(_to_step_result("extraction_summary", ex_outcome, ex_start))

    cr_start = _now()
    cr_outcome = _safe_step("criteria_summary", load_criteria_summary, case_id, conn)
    steps.append(_to_step_result("criteria_summary", cr_outcome, cr_start))

    nr_start = _now()
    nr_outcome = _safe_step(
        "normalization_summary", load_normalization_summary, case_id, conn
    )
    steps.append(_to_step_result("normalization_summary", nr_outcome, nr_start))

    sc_start = _now()
    sc_outcome = _safe_step("scoring", run_scoring_step, case_id, conn, force_recompute)
    steps.append(_to_step_result("scoring", sc_outcome, sc_start))

    cas = build_case_analysis_snapshot(case_id, steps, case_row)

    step_statuses = {s.status for s in steps}
    if "failed" in step_statuses:
        pipeline_status = "failed"
    elif "blocked" in step_statuses:
        pipeline_status = "blocked"
    elif "incomplete" in step_statuses:
        pipeline_status = "incomplete"
    else:
        pipeline_status = "partial_complete"

    warnings: list[dict[str, Any]] = [
        {
            "step": s.step_name,
            "reason_code": s.reason_code,
            "reason_message": s.reason_message,
        }
        for s in steps
        if s.status not in ("ok", "skipped") and s.reason_code
    ]

    finished_at = _now()
    dur = _duration_ms(started_at, finished_at)

    persist_pipeline_run_and_steps(
        conn,
        run_id,
        case_id,
        triggered_by,
        pipeline_status,
        started_at,
        finished_at,
        dur,
        steps,
        cas,
        force_recompute=force_recompute,
        mode="e2e",
    )

    errors: list[str] = [
        s.reason_message or s.reason_code or ""
        for s in steps
        if s.status in ("failed", "blocked") and s.reason_code
    ]

    return PipelineResult(
        run_id=run_id,
        case_id=case_id,
        status=pipeline_status,
        mode="e2e",
        force_recompute=force_recompute,
        steps=steps,
        cas=cas,
        triggered_by=triggered_by,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=dur,
        warnings=warnings,
        errors=errors,
    )
