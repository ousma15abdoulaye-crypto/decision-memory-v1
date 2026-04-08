# src/couche_a/pipeline/service_utils.py
"""
Shared utilities for the pipeline service — time, JSON, step wrappers.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from .models import (
    CaseAnalysisSnapshot,
    PipelineLastRunResponse,
    PipelineStepName,
    PipelineStepResult,
    StepOutcome,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _duration_ms(start: datetime, end: datetime) -> int:
    """INV-P12 : duration_ms ≥ 0, protégé contre NTP drift."""
    return max(0, int((end - start).total_seconds() * 1000))


def _json_safe(v: Any) -> Any:
    """Convertit une valeur en type JSON-serializable."""
    if v is None or isinstance(v, bool | int | float | str):
        return v
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, dict):
        return {k: _json_safe(vv) for k, vv in v.items()}
    if isinstance(v, list):
        return [_json_safe(item) for item in v]
    return str(v)


def _to_step_result(
    name: PipelineStepName,
    outcome: StepOutcome,
    step_start: datetime,
) -> PipelineStepResult:
    """Convertit un StepOutcome en PipelineStepResult horodaté."""
    step_end = _now()
    return PipelineStepResult(
        step_name=name,
        status=outcome.status,
        started_at=step_start,
        finished_at=step_end,
        duration_ms=_duration_ms(step_start, step_end),
        reason_code=outcome.reason_code,
        reason_message=outcome.reason_message,
        meta=outcome.meta,
    )


def _safe_step(name: str, fn: Any, *args: Any, **kwargs: Any) -> StepOutcome:
    """Exécute un step en capturant les exceptions applicatives."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        return StepOutcome(
            status="failed",
            reason_code="STEP_EXCEPTION",
            reason_message=str(exc)[:500],
        )


def persist_pipeline_run_and_steps(
    conn: Any,
    run_id: str,
    case_id: str,
    triggered_by: str,
    status: str,
    started_at: datetime,
    finished_at: datetime,
    duration_ms: int,
    steps: list[PipelineStepResult],
    cas: CaseAnalysisSnapshot | None,
    force_recompute: bool = False,
    mode: str = "partial",
) -> None:
    """
    Insère pipeline_runs + pipeline_step_runs de manière atomique.
    Pattern B : pas de conn.commit() — le context manager du router commit.
    """
    result_jsonb = json.dumps(_json_safe(cas.model_dump()) if cas else {})
    error_jsonb = "[]"

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.pipeline_runs
                (pipeline_run_id, case_id, pipeline_type, mode, status,
                 started_at, finished_at, duration_ms, triggered_by,
                 result_jsonb, error_jsonb, force_recompute)
            VALUES (%s, %s, 'A', %s, %s,
                    %s, %s, %s, %s,
                    %s::jsonb, %s::jsonb, %s)
            """,
            (
                run_id,
                case_id,
                mode,
                status,
                started_at,
                finished_at,
                duration_ms,
                triggered_by,
                result_jsonb,
                error_jsonb,
                force_recompute,
            ),
        )

        for step in steps:
            step_meta_json = json.dumps(_json_safe(step.meta))
            cur.execute(
                """
                INSERT INTO public.pipeline_step_runs
                    (pipeline_run_id, step_name, status,
                     started_at, finished_at, duration_ms,
                     reason_code, reason_message, meta_jsonb)
                VALUES (%s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s::jsonb)
                """,
                (
                    run_id,
                    step.step_name,
                    step.status,
                    step.started_at,
                    step.finished_at,
                    step.duration_ms,
                    step.reason_code,
                    step.reason_message,
                    step_meta_json,
                ),
            )


def get_last_pipeline_run(case_id: str, conn: Any) -> PipelineLastRunResponse | None:
    """Récupère le dernier run depuis pipeline_runs.result_jsonb."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT pipeline_run_id, case_id, status, triggered_by,
                   started_at, finished_at, duration_ms, result_jsonb, created_at
            FROM public.pipeline_runs
            WHERE case_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (case_id,),
        )
        row = cur.fetchone()

    if not row:
        return None

    return PipelineLastRunResponse.from_db_row(dict(row))
