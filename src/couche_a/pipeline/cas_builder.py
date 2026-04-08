# src/couche_a/pipeline/cas_builder.py
"""
Build CaseAnalysisSnapshot (CAS v1) from pipeline step results.
"""

from __future__ import annotations

from typing import Any

from .models import (
    CASCaseContext,
    CASCriteriaSummary,
    CaseAnalysisSnapshot,
    CASOfferSummary,
    CASReadiness,
    CASScoreSummary,
    PipelineStepResult,
)
from .service_utils import _json_safe, _now

_MIN_OFFERS_REQUIRED = 2


def load_case_row(case_id: str, conn: Any) -> dict[str, Any] | None:
    """Charge la ligne cases depuis DB."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, currency, status, case_type, lot, "
            "estimated_value, procedure_type "
            "FROM public.cases WHERE id = %s",
            (case_id,),
        )
        return cur.fetchone()


def build_case_analysis_snapshot(
    case_id: str,
    steps: list[PipelineStepResult],
    case_row: dict[str, Any],
) -> CaseAnalysisSnapshot:
    """
    Construit CAS v1 depuis les meta des steps.
    Toutes les données viennent de step.meta (unique canal — V2.2).
    """
    pf_step = next((s for s in steps if s.step_name == "preflight"), None)
    criteria_step = next((s for s in steps if s.step_name == "criteria_summary"), None)
    extraction_step = next(
        (s for s in steps if s.step_name == "extraction_summary"), None
    )
    scoring_step = next((s for s in steps if s.step_name == "scoring"), None)

    case_context = CASCaseContext(
        case_id=case_id,
        title=str(case_row.get("title", "")),
        currency=str(case_row.get("currency", "XOF")),
        status=str(case_row.get("status", "")),
        case_type=str(case_row.get("case_type", "")),
        lot=case_row.get("lot"),
        estimated_value=(
            float(case_row["estimated_value"])
            if case_row.get("estimated_value") is not None
            else None
        ),
        procedure_type=case_row.get("procedure_type"),
    )

    offers_count = int((pf_step.meta if pf_step else {}).get("offers_count", 0))
    supplier_names = list(
        (extraction_step.meta if extraction_step else {}).get("supplier_names", [])
    )

    criteria_meta = (
        criteria_step.meta if criteria_step and criteria_step.status == "ok" else {}
    )
    scoring_meta = (
        scoring_step.meta if scoring_step and scoring_step.status == "ok" else {}
    )

    has_scoring = bool(scoring_meta.get("scores_count", 0) > 0)
    has_criteria = bool(criteria_meta.get("count", 0) > 0)
    has_offers = offers_count >= _MIN_OFFERS_REQUIRED

    blocking_reasons: list[str] = []
    if not has_criteria:
        blocking_reasons.append("no_criteria")
    if not has_offers:
        blocking_reasons.append("insufficient_offers")
    if not has_scoring:
        blocking_reasons.append("no_scores")

    return CaseAnalysisSnapshot(
        cas_version="v1",
        case_context=case_context,
        readiness=CASReadiness(
            export_ready=False,
            has_scoring=has_scoring,
            has_criteria=has_criteria,
            has_offers=has_offers,
            blocking_reasons=blocking_reasons,
        ),
        criteria_summary=CASCriteriaSummary(
            count=int(criteria_meta.get("count", 0)),
            categories=list(criteria_meta.get("categories", [])),
            has_eliminatory=bool(criteria_meta.get("has_eliminatory", False)),
        ),
        offer_summary=CASOfferSummary(
            count=offers_count,
            supplier_names=supplier_names,
            complete_count=sum(1 for s in supplier_names if "COMPLETE" in str(s)),
            partial_count=0,
        ),
        score_summary=CASScoreSummary(
            scores_count=int(scoring_meta.get("scores_count", 0)),
            eliminations_count=int(scoring_meta.get("eliminations_count", 0)),
            score_entries=[
                _json_safe(e) for e in scoring_meta.get("score_entries", [])
            ],
        ),
        steps=steps,
        generated_at=_now(),
    )
