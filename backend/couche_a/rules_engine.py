"""Couche A – Business rules engine for submission evaluation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.couche_a.models import PreanalysisResult, Submission

__all__ = [
    "check_essential_criteria",
    "score_capacity",
    "score_durability",
    "score_commercial",
    "evaluate_submission",
]


def check_essential_criteria(preanalysis: list[dict]) -> tuple[bool, list[str]]:
    """Verify mandatory documents are present. Returns (pass, reasons)."""
    reasons: list[str] = []
    has_tech = any(p.get("detected_type") == "TECH" for p in preanalysis)
    has_fin = any(p.get("detected_type") == "FIN" for p in preanalysis)

    if not has_tech:
        reasons.append("Missing technical offer document")
    if not has_fin:
        reasons.append("Missing financial offer document")

    return (len(reasons) == 0, reasons)


def score_capacity(preanalysis: list[dict]) -> float:
    """Score vendor capacity (max 40 points)."""
    score = 0.0
    has_tech = any(p.get("detected_type") == "TECH" for p in preanalysis)
    has_checklist = any(p.get("doc_checklist", {}).get("has_technical") for p in preanalysis)

    if has_tech:
        score += 20.0
    if has_checklist:
        score += 10.0
    # Additional capacity signals
    if any(p.get("vendor_name") for p in preanalysis):
        score += 10.0

    return min(score, 40.0)


def score_durability(preanalysis: list[dict]) -> float:
    """Score sustainability / durability criteria (max 20 points)."""
    score = 0.0
    # Placeholder: award points if no flags
    for p in preanalysis:
        flags = p.get("flags", {})
        if not flags:
            score += 10.0
            break
    # Base points for having a submission
    if preanalysis:
        score += 10.0
    return min(score, 20.0)


def score_commercial(preanalysis: list[dict]) -> float:
    """Score commercial / financial criteria (max 40 points)."""
    score = 0.0
    has_fin = any(p.get("detected_type") == "FIN" for p in preanalysis)
    has_amount = any(p.get("amount") for p in preanalysis)

    if has_fin:
        score += 20.0
    if has_amount:
        score += 20.0

    return min(score, 40.0)


async def evaluate_submission(submission_id: str, db: AsyncSession) -> dict:
    """Run full evaluation for a submission. Returns scores and status."""
    stmt = select(PreanalysisResult).where(PreanalysisResult.submission_id == submission_id)
    results = (await db.execute(stmt)).scalars().all()

    preanalysis = [
        {
            "detected_type": r.detected_type,
            "doc_checklist": r.doc_checklist or {},
            "flags": r.flags or {},
            "vendor_name": r.vendor_name,
            "amount": r.amount,
        }
        for r in results
    ]

    essential_pass, reasons = check_essential_criteria(preanalysis)
    cap = score_capacity(preanalysis)
    dur = score_durability(preanalysis)
    com = score_commercial(preanalysis)
    total = cap + dur + com

    if not essential_pass:
        eval_status = "NON_CONF"
    elif total >= 60.0:
        eval_status = "CONF"
    else:
        eval_status = "REVUE_MANUELLE"

    # Update submission status
    sub_stmt = select(Submission).where(Submission.id == submission_id)
    sub = (await db.execute(sub_stmt)).scalar_one_or_none()
    if sub:
        sub.status = eval_status
        await db.flush()

    return {
        "submission_id": submission_id,
        "essential_pass": essential_pass,
        "essential_reasons": reasons,
        "scores": {"capacity": cap, "durability": dur, "commercial": com},
        "total": total,
        "status": eval_status,
    }
