# src/couche_a/pipeline/service.py
"""
Orchestrateur Pipeline A — Couche A uniquement (ADR-0012).

Séquence : preflight → extraction_summary → criteria_summary
           → normalization_summary → scoring → build CAS v1 → persist atomique.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from src.core.models import DAOCriterion, SupplierPackage
from src.couche_a.scoring.engine import ScoringEngine

from .cas_builder import build_case_analysis_snapshot, load_case_row
from .models import PipelineResult, PipelineStepResult, StepOutcome
from .service_utils import (
    _duration_ms,
    _now,
    _safe_step,
    _to_step_result,
    get_last_pipeline_run,  # noqa: F401 — re-exported for router.py
    persist_pipeline_run_and_steps,
)
from .steps import (
    RC_CASE_NOT_FOUND,  # noqa: F401 — re-exported for tests
    RC_DAO_MISSING,  # noqa: F401 — re-exported for tests
    RC_MIN_OFFERS_INSUFFICIENT,  # noqa: F401 — re-exported for tests
    RC_OFFERS_MISSING,  # noqa: F401 — re-exported for tests
)
from .steps import (
    load_criteria_summary as _load_criteria_summary,
)
from .steps import (
    load_extraction_summary as _load_extraction_summary,
)
from .steps import (
    load_normalization_summary as _load_normalization_summary,
)
from .steps import (
    preflight_case_a_partial as _preflight_case_a_partial,
)

# ---------------------------------------------------------------------------
# Scoring helpers (kept here for monkeypatch compatibility with tests)
# ---------------------------------------------------------------------------


def _build_supplier_packages_from_extractions(
    extractions: list[dict[str, Any]],
) -> list[SupplierPackage]:
    """Reconstruit des SupplierPackage minimaux depuis offer_extractions."""
    by_supplier: dict[str, dict[str, Any]] = {}
    for row in extractions:
        sn = row["supplier_name"]
        if sn not in by_supplier:
            by_supplier[sn] = {
                "supplier_name": sn,
                "offer_ids": [],
                "documents": [],
                "extracted_data": {},
                "missing_fields": [],
            }
        try:
            data = json.loads(row.get("extracted_data_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            data = {}
        by_supplier[sn]["extracted_data"].update(data)
        by_supplier[sn]["offer_ids"].append(row.get("id", ""))

    packages = []
    for sn, info in by_supplier.items():
        ext = info["extracted_data"]
        packages.append(
            SupplierPackage(
                supplier_name=sn,
                offer_ids=info["offer_ids"],
                documents=info["documents"],
                package_status=ext.get("package_status", "PARTIAL"),
                has_financial=bool(ext.get("has_financial", False)),
                has_technical=bool(ext.get("has_technical", False)),
                has_admin=bool(ext.get("has_admin", False)),
                extracted_data=ext,
                missing_fields=ext.get("missing_fields", []),
            )
        )
    return packages


def _build_dao_criteria_from_rows(rows: list[dict[str, Any]]) -> list[DAOCriterion]:
    """Convertit des lignes dao_criteria en DAOCriterion pour le ScoringEngine."""
    return [
        DAOCriterion(
            categorie=r.get("categorie", ""),
            critere_nom=r.get("critere_nom", ""),
            description=r.get("description") or "",
            ponderation=float(r.get("ponderation") or 0.0),
            type_reponse=r.get("type_reponse", ""),
            seuil_elimination=(
                float(r["seuil_elimination"])
                if r.get("seuil_elimination") is not None
                else None
            ),
            ordre_affichage=int(r.get("ordre_affichage") or 0),
        )
        for r in rows
    ]


def _run_scoring_step(
    case_id: str,
    conn: Any,
    force_recompute: bool = False,
) -> StepOutcome:
    """Délègue le scoring au ScoringEngine existant."""

    with conn.cursor() as cur:
        cur.execute(
            "SELECT oe.id, oe.supplier_name, oe.extracted_data_json "
            "FROM public.offer_extractions oe "
            "INNER JOIN process_workspaces pw ON pw.id = oe.workspace_id "
            "WHERE pw.legacy_case_id = %s",
            (case_id,),
        )
        extractions = cur.fetchall()

        cur.execute(
            "SELECT dc.categorie, dc.critere_nom, dc.description, dc.ponderation, "
            "dc.type_reponse, dc.seuil_elimination, dc.ordre_affichage, dc.is_eliminatory "
            "FROM public.dao_criteria dc "
            "INNER JOIN process_workspaces pw ON pw.id = dc.workspace_id "
            "WHERE pw.legacy_case_id = %s",
            (case_id,),
        )
        criteria_rows = cur.fetchall()

    if not extractions:
        return StepOutcome(
            status="incomplete",
            reason_code="NO_EXTRACTIONS_FOR_SCORING",
            reason_message=(
                f"Aucune extraction disponible pour scorer case_id={case_id!r}"
            ),
            meta={"scores_count": 0, "eliminations_count": 0},
        )

    supplier_packages = _build_supplier_packages_from_extractions(extractions)
    criteria = _build_dao_criteria_from_rows(criteria_rows)
    engine = ScoringEngine()

    # Calcul direct (Option 2 rectificatif CTO P3.3) — pas de cache score sur
    # méthode absente / AttributeError sur chemin nominal.
    scores, eliminations = engine.calculate_scores_for_case(
        case_id=case_id,
        suppliers=supplier_packages,
        criteria=criteria,
    )

    score_entries = [
        {
            "supplier_name": s.supplier_name,
            "category": s.category,
            "score_value": float(s.score_value),
        }
        for s in scores
    ]

    meta: dict[str, Any] = {
        "scores_count": len(scores),
        "eliminations_count": len(eliminations),
        "score_entries": score_entries,
        "force_recompute": force_recompute,
    }

    return StepOutcome(
        status="ok" if scores else "incomplete",
        reason_code=None if scores else "NO_SCORES_COMPUTED",
        reason_message=(
            None if scores else f"Aucun score calculé pour case_id={case_id!r}"
        ),
        meta=meta,
    )


run_scoring_step = _run_scoring_step


# ---------------------------------------------------------------------------
# Pipeline orchestrators
# ---------------------------------------------------------------------------


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
    pf_outcome = _safe_step("preflight", _preflight_case_a_partial, case_id, conn)
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
        "extraction_summary", _load_extraction_summary, case_id, conn
    )
    steps.append(_to_step_result("extraction_summary", ex_outcome, ex_start))

    cr_start = _now()
    cr_outcome = _safe_step("criteria_summary", _load_criteria_summary, case_id, conn)
    steps.append(_to_step_result("criteria_summary", cr_outcome, cr_start))

    nr_start = _now()
    nr_outcome = _safe_step(
        "normalization_summary", _load_normalization_summary, case_id, conn
    )
    steps.append(_to_step_result("normalization_summary", nr_outcome, nr_start))

    sc_start = _now()
    sc_outcome = _safe_step("scoring", _run_scoring_step, case_id, conn)
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
    pf_outcome = _safe_step("preflight", _preflight_case_a_partial, case_id, conn)
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
        "extraction_summary", _load_extraction_summary, case_id, conn
    )
    steps.append(_to_step_result("extraction_summary", ex_outcome, ex_start))

    cr_start = _now()
    cr_outcome = _safe_step("criteria_summary", _load_criteria_summary, case_id, conn)
    steps.append(_to_step_result("criteria_summary", cr_outcome, cr_start))

    nr_start = _now()
    nr_outcome = _safe_step(
        "normalization_summary", _load_normalization_summary, case_id, conn
    )
    steps.append(_to_step_result("normalization_summary", nr_outcome, nr_start))

    sc_start = _now()
    sc_outcome = _safe_step(
        "scoring", _run_scoring_step, case_id, conn, force_recompute
    )
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
