"""Learning console — corrections, patterns, candidate rules, RAGAS history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.views.learning_console_models import (
    CandidateRuleSummary,
    CorrectionSummary,
    LearningConsoleData,
    PatternSummary,
    RAGASHistoryEntry,
    RuleActionResponse,
)
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.db.connection import get_db_cursor
from src.db.cursor_adapter import PsycopgCursorAdapter

router = APIRouter(prefix="/views/learning", tags=["learning"])

_CORRECTION_SUMMARY_SQL = """
    SELECT
        COUNT(*)::int                                               AS total_corrections,
        COUNT(*) FILTER (
            WHERE created_at >= NOW() - INTERVAL '30 days'
        )::float / NULLIF(
            (SELECT COUNT(*) FROM m13_correction_log
             WHERE created_at >= NOW() - INTERVAL '30 days'), 0
        )                                                           AS correction_rate_30d
    FROM m13_correction_log
"""

_TOP_FIELDS_SQL = """
    SELECT field_path, COUNT(*)::int AS cnt
    FROM m13_correction_log
    GROUP BY field_path
    ORDER BY cnt DESC
    LIMIT 5
"""

_CANDIDATE_RULES_SQL = """
    SELECT rule_id, status, change_type,
           COALESCE(change_detail::text, '') AS change_detail
    FROM public.candidate_rules
    ORDER BY proposed_at DESC
    LIMIT 50
"""

_CANDIDATE_RULES_BY_STATUS_SQL = """
    SELECT rule_id, status, change_type,
           COALESCE(change_detail::text, '') AS change_detail
    FROM public.candidate_rules
    WHERE status = %(status)s
    ORDER BY proposed_at DESC
    LIMIT 50
"""

_RAGAS_HISTORY_SQL = """
    SELECT
        created_at::text        AS evaluated_at,
        (metadata->>'overall_score')::float         AS overall_score,
        (metadata->>'context_precision')::float     AS context_precision,
        (metadata->>'faithfulness')::float          AS faithfulness,
        (metadata->>'answer_relevancy')::float      AS answer_relevancy
    FROM public.llm_traces
    WHERE operation = 'ragas_evaluation'
    ORDER BY created_at DESC
    LIMIT 20
"""

_UPDATE_RULE_STATUS_SQL = """
    UPDATE public.candidate_rules
    SET status      = %(new_status)s,
        reviewed_at = NOW(),
        reviewed_by = %(user_id)s
    WHERE rule_id = %(rule_id)s
    RETURNING rule_id
"""

_CHECK_RULE_EXISTS_SQL = """
    SELECT rule_id FROM public.candidate_rules
    WHERE rule_id = %(rule_id)s
"""

_INSERT_RULE_PROMOTION_SQL = """
    INSERT INTO public.rule_promotions (
        candidate_rule_id, promotion_type,
        config_file_path, config_diff, applied_by
    )
    VALUES (
        %(rule_id)s,
        'approved',
        'candidate_rules',
        %(user_id)s,
        %(user_id)s
    )
    ON CONFLICT DO NOTHING
"""


@router.get("/console", response_model=LearningConsoleData)
def get_learning_console() -> LearningConsoleData:
    try:
        with get_db_cursor() as cur:
            adapter = PsycopgCursorAdapter(cur)

            # Correction summary
            adapter.execute(_CORRECTION_SUMMARY_SQL)
            row = adapter.fetchone()
            total_corr = int(row["total_corrections"]) if row else 0
            rate = float(row["correction_rate_30d"] or 0.0) if row else 0.0

            adapter.execute(_TOP_FIELDS_SQL)
            field_rows = adapter.fetchall()
            top_fields = [
                str(r["field_path"]) for r in field_rows if r.get("field_path")
            ]

            corrections = CorrectionSummary(
                total_corrections=total_corr,
                correction_rate_30d=round(rate, 4),
                top_fields=top_fields,
            )

            # Patterns via PatternDetector
            patterns: list[PatternSummary] = []
            try:
                from src.memory.pattern_detector import PatternDetector

                pd = PatternDetector(lambda: adapter)
                detected = pd.detect_all()
                patterns = [
                    PatternSummary(
                        pattern_type=p.pattern_type.value,
                        field_path=p.field_path,
                        occurrences=p.occurrences,
                        confidence=p.confidence,
                    )
                    for p in detected
                ]
            except Exception:
                pass

            # Candidate rules
            candidate_rules: list[CandidateRuleSummary] = []
            try:
                adapter.execute(_CANDIDATE_RULES_SQL)
                rule_rows = adapter.fetchall()
                candidate_rules = [
                    CandidateRuleSummary(
                        rule_id=str(r["rule_id"]),
                        status=str(r["status"]),
                        change_type=str(r["change_type"]),
                        change_detail=str(r.get("change_detail") or ""),
                    )
                    for r in rule_rows
                ]
            except Exception:
                pass

            # Calibration status
            calibration_status = "healthy"
            try:
                from src.memory.calibration_service import CalibrationService

                svc = CalibrationService(lambda: adapter)
                report = svc.assess()
                calibration_status = report.status.value
            except Exception:
                pass

            return LearningConsoleData(
                corrections=corrections,
                patterns=patterns,
                candidate_rules=candidate_rules,
                calibration_status=calibration_status,
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/patterns", response_model=list[PatternSummary])
def get_patterns() -> list[PatternSummary]:
    try:
        with get_db_cursor() as cur:
            adapter = PsycopgCursorAdapter(cur)
            from src.memory.pattern_detector import PatternDetector

            pd = PatternDetector(lambda: adapter)
            detected = pd.detect_all()
            return [
                PatternSummary(
                    pattern_type=p.pattern_type.value,
                    field_path=p.field_path,
                    occurrences=p.occurrences,
                    confidence=p.confidence,
                )
                for p in detected
            ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/rules", response_model=list[CandidateRuleSummary])
def get_candidate_rules(status: str | None = None) -> list[CandidateRuleSummary]:
    try:
        with get_db_cursor() as cur:
            adapter = PsycopgCursorAdapter(cur)
            if status:
                adapter.execute(_CANDIDATE_RULES_BY_STATUS_SQL, {"status": status})
            else:
                adapter.execute(_CANDIDATE_RULES_SQL)
            rows = adapter.fetchall()
            return [
                CandidateRuleSummary(
                    rule_id=str(r["rule_id"]),
                    status=str(r["status"]),
                    change_type=str(r["change_type"]),
                    change_detail=str(r.get("change_detail") or ""),
                )
                for r in rows
            ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def approve_rule_core(rule_id: str, user_id: str) -> RuleActionResponse:
    """Approuve une règle candidate (logique pure — tests sans stack FastAPI)."""
    try:
        with get_db_cursor() as cur:
            adapter = PsycopgCursorAdapter(cur)
            adapter.execute(
                _UPDATE_RULE_STATUS_SQL,
                {"new_status": "approved", "rule_id": rule_id, "user_id": user_id},
            )
            try:
                adapter.execute(
                    _INSERT_RULE_PROMOTION_SQL,
                    {"rule_id": rule_id, "user_id": user_id},
                )
            except Exception:
                pass
    except Exception:
        pass
    return RuleActionResponse(
        rule_id=rule_id,
        new_status="approved",
        message=f"Rule {rule_id} approved by {user_id}",
    )


def reject_rule_core(rule_id: str, user_id: str) -> RuleActionResponse:
    """Rejette une règle candidate (logique pure — tests sans stack FastAPI)."""
    try:
        with get_db_cursor() as cur:
            adapter = PsycopgCursorAdapter(cur)
            adapter.execute(
                _UPDATE_RULE_STATUS_SQL,
                {"new_status": "rejected", "rule_id": rule_id, "user_id": user_id},
            )
    except Exception:
        pass
    return RuleActionResponse(
        rule_id=rule_id,
        new_status="rejected",
        message=f"Rule {rule_id} rejected by {user_id}",
    )


@router.post("/rules/{rule_id}/approve", response_model=RuleActionResponse)
def approve_rule(
    rule_id: str,
    current_user: UserClaims = Depends(get_current_user),
) -> RuleActionResponse:
    return approve_rule_core(rule_id, str(current_user.user_id))


@router.post("/rules/{rule_id}/reject", response_model=RuleActionResponse)
def reject_rule(
    rule_id: str,
    current_user: UserClaims = Depends(get_current_user),
) -> RuleActionResponse:
    return reject_rule_core(rule_id, str(current_user.user_id))


@router.get("/ragas-history", response_model=list[RAGASHistoryEntry])
def get_ragas_history() -> list[RAGASHistoryEntry]:
    try:
        with get_db_cursor() as cur:
            adapter = PsycopgCursorAdapter(cur)
            adapter.execute(_RAGAS_HISTORY_SQL)
            rows = adapter.fetchall()
            out: list[RAGASHistoryEntry] = []
            for r in rows:
                try:
                    out.append(
                        RAGASHistoryEntry(
                            evaluated_at=str(r.get("evaluated_at") or ""),
                            overall_score=float(r.get("overall_score") or 0.0),
                            context_precision=float(r.get("context_precision") or 0.0),
                            faithfulness=float(r.get("faithfulness") or 0.0),
                            answer_relevancy=float(r.get("answer_relevancy") or 0.0),
                        )
                    )
                except Exception:
                    continue
            return out
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
