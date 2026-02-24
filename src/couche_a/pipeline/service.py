# src/couche_a/pipeline/service.py
"""
Orchestrateur Pipeline A — Couche A uniquement (ADR-0012).

Séquence : preflight → extraction_summary → criteria_summary
           → normalization_summary → scoring → build CAS v1 → persist atomique.

Pattern DB : Pattern B — le router injecte une connexion psycopg autocommit=False.
             _persist_pipeline_run_and_steps() n'appelle PAS conn.commit() :
             le context manager du router (ou du test) commit à la sortie du scope.

Les exceptions intra-step sont structurées via _safe_step().
Les erreurs de persistance DB restent volontairement fail-fast pour préserver
la vérité d'exécution (violation de contrainte DB = signal CI, pas silence).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.core.models import DAOCriterion, SupplierPackage
from src.couche_a.scoring.engine import ScoringEngine

from .models import (
    CASCaseContext,
    CASCriteriaSummary,
    CaseAnalysisSnapshot,
    CASOfferSummary,
    CASReadiness,
    CASScoreSummary,
    PipelineLastRunResponse,
    PipelineResult,
    PipelineStepName,
    PipelineStepResult,
    StepOutcome,
)

# ---------------------------------------------------------------------------
# Constantes preflight — 4 reason_codes exacts (INV-P préflight uniquement)
# ---------------------------------------------------------------------------

RC_CASE_NOT_FOUND = "CASE_NOT_FOUND"
RC_DAO_MISSING = "DAO_MISSING"
RC_OFFERS_MISSING = "OFFERS_MISSING"
RC_MIN_OFFERS_INSUFFICIENT = "MIN_OFFERS_INSUFFICIENT"

_MIN_OFFERS_REQUIRED = 2

# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _duration_ms(start: datetime, end: datetime) -> int:
    """INV-P12 : duration_ms ≥ 0, protégé contre NTP drift."""
    return max(0, int((end - start).total_seconds() * 1000))


def _json_safe(v: Any) -> Any:
    """
    Convertit une valeur en type JSON-serializable.
    JSON natifs inchangés. datetime/date/UUID/Decimal → str.
    Fallback → str.
    """
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
    """
    Exécute un step en capturant les exceptions applicatives.
    Les erreurs de persistance DB restent volontairement non interceptées ici.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        return StepOutcome(
            status="failed",
            reason_code="STEP_EXCEPTION",
            reason_message=str(exc)[:500],
        )


# ---------------------------------------------------------------------------
# Step 1 : Preflight
# ---------------------------------------------------------------------------


def _preflight_case_a_partial(case_id: str, conn: Any) -> StepOutcome:
    """
    Préflight A/partial — 4 reason_codes exacts (INV-P préflight uniquement).

    CASE_NOT_FOUND       : le case n'existe pas dans public.cases.
    DAO_MISSING          : aucun critère DAO dans public.dao_criteria pour ce case.
    OFFERS_MISSING       : aucune offre dans public.offers pour ce case.
    MIN_OFFERS_INSUFFICIENT : moins de 2 offres (minimum requis pour pipeline A).
    """
    with conn.cursor() as cur:
        # Check 1 : case existe
        cur.execute(
            "SELECT id, title, currency, status, case_type, lot, "
            "estimated_value, procedure_type "
            "FROM public.cases WHERE id = %s",
            (case_id,),
        )
        case_row = cur.fetchone()

    if not case_row:
        return StepOutcome(
            status="blocked",
            reason_code=RC_CASE_NOT_FOUND,
            reason_message=f"Aucun dossier trouvé pour case_id={case_id!r}",
            meta={"case_id": case_id, "dao_present": False, "offers_count": 0},
        )

    with conn.cursor() as cur:
        # Check 2 : DAO critères présents
        cur.execute(
            "SELECT COUNT(*) AS n FROM public.dao_criteria WHERE case_id = %s",
            (case_id,),
        )
        dao_count = cur.fetchone()["n"]

    if dao_count == 0:
        return StepOutcome(
            status="blocked",
            reason_code=RC_DAO_MISSING,
            reason_message=(
                f"Aucun critère DAO pour case_id={case_id!r} — "
                "charger le DAO avant de lancer le pipeline"
            ),
            meta={"case_id": case_id, "dao_present": False, "offers_count": 0},
        )

    with conn.cursor() as cur:
        # Check 3 : offres présentes
        cur.execute(
            "SELECT COUNT(*) AS n FROM public.offers WHERE case_id = %s",
            (case_id,),
        )
        offers_count = cur.fetchone()["n"]

    if offers_count == 0:
        return StepOutcome(
            status="blocked",
            reason_code=RC_OFFERS_MISSING,
            reason_message=(
                f"Aucune offre pour case_id={case_id!r} — "
                "charger les offres avant de lancer le pipeline"
            ),
            meta={"case_id": case_id, "dao_present": True, "offers_count": 0},
        )

    # Check 4 : minimum 2 offres
    if offers_count < _MIN_OFFERS_REQUIRED:
        return StepOutcome(
            status="blocked",
            reason_code=RC_MIN_OFFERS_INSUFFICIENT,
            reason_message=(
                f"Pipeline A requiert au minimum {_MIN_OFFERS_REQUIRED} offres — "
                f"trouvé {offers_count} pour case_id={case_id!r}"
            ),
            meta={
                "case_id": case_id,
                "dao_present": True,
                "offers_count": offers_count,
            },
        )

    return StepOutcome(
        status="ok",
        meta={
            "case_id": case_id,
            "dao_present": True,
            "offers_count": offers_count,
            "dao_count": dao_count,
        },
    )


# ---------------------------------------------------------------------------
# Step 2 : Extraction summary (lecture seule)
# ---------------------------------------------------------------------------


def _load_extraction_summary(case_id: str, conn: Any) -> StepOutcome:
    """
    Résumé des extractions disponibles dans offer_extractions.
    Lecture seule — aucune écriture.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT supplier_name, extracted_data_json "
            "FROM public.offer_extractions WHERE case_id = %s",
            (case_id,),
        )
        rows = cur.fetchall()

    suppliers = [r["supplier_name"] for r in rows]
    return StepOutcome(
        status="ok" if rows else "incomplete",
        reason_code=None if rows else "NO_EXTRACTIONS",
        reason_message=(
            None if rows else f"Aucune extraction disponible pour case_id={case_id!r}"
        ),
        meta={
            "extractions_count": len(rows),
            "supplier_names": suppliers,
        },
    )


# ---------------------------------------------------------------------------
# Step 3 : Criteria summary (lecture seule)
# ---------------------------------------------------------------------------


def _load_criteria_summary(case_id: str, conn: Any) -> StepOutcome:
    """
    Résumé des critères DAO dans dao_criteria.
    Lecture seule — aucune écriture.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT categorie, is_eliminatory "
            "FROM public.dao_criteria WHERE case_id = %s",
            (case_id,),
        )
        rows = cur.fetchall()

    if not rows:
        return StepOutcome(
            status="incomplete",
            reason_code="NO_CRITERIA",
            reason_message=f"Aucun critère trouvé pour case_id={case_id!r}",
            meta={"count": 0, "categories": [], "has_eliminatory": False},
        )

    categories = sorted(set(r["categorie"] for r in rows if r["categorie"]))
    has_eliminatory = any(r.get("is_eliminatory") for r in rows)

    return StepOutcome(
        status="ok",
        meta={
            "count": len(rows),
            "categories": categories,
            "has_eliminatory": has_eliminatory,
        },
    )


# ---------------------------------------------------------------------------
# Step 4 : Normalization summary (lecture seule)
# ---------------------------------------------------------------------------


def _load_normalization_summary(case_id: str, conn: Any) -> StepOutcome:
    """
    Résumé de la normalisation : score_runs existants pour ce case.
    Lecture seule — aucune écriture.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM public.score_runs WHERE case_id = %s",
            (case_id,),
        )
        n = cur.fetchone()["n"]

    return StepOutcome(
        status="ok",
        meta={
            "existing_score_runs": n,
            "note": "score_runs existants — le scoring step créera de nouveaux runs",
        },
    )


# ---------------------------------------------------------------------------
# Step 5 : Scoring (délégation ScoringEngine)
# ---------------------------------------------------------------------------


def _build_supplier_packages_from_extractions(
    extractions: list[dict[str, Any]],
) -> list[SupplierPackage]:
    """
    Reconstruit des SupplierPackage minimaux depuis offer_extractions.
    Agrège par supplier_name.
    """
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


def _run_scoring_step(case_id: str, conn: Any) -> StepOutcome:
    """
    Délègue le scoring au ScoringEngine existant.
    Charge offer_extractions + dao_criteria depuis DB.
    ScoringEngine gère ses propres connexions DB (score_runs append-only).
    Lecture des données de base via la connexion injectée.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, supplier_name, extracted_data_json "
            "FROM public.offer_extractions WHERE case_id = %s",
            (case_id,),
        )
        extractions = cur.fetchall()

        cur.execute(
            "SELECT categorie, critere_nom, description, ponderation, "
            "type_reponse, seuil_elimination, ordre_affichage, is_eliminatory "
            "FROM public.dao_criteria WHERE case_id = %s",
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
    scores, eliminations = engine.calculate_scores_for_case(
        case_id=case_id,
        suppliers=supplier_packages,
        criteria=criteria,
    )

    if scores:
        engine._save_scores_to_db(case_id, scores)

    score_entries = [
        {
            "supplier_name": s.supplier_name,
            "category": s.category,
            "score_value": float(s.score_value),
        }
        for s in scores
    ]

    return StepOutcome(
        status="ok" if scores else "incomplete",
        reason_code=None if scores else "NO_SCORES_COMPUTED",
        reason_message=(
            None if scores else f"Aucun score calculé pour case_id={case_id!r}"
        ),
        meta={
            "scores_count": len(scores),
            "eliminations_count": len(eliminations),
            "score_entries": score_entries,
        },
    )


# ---------------------------------------------------------------------------
# Build CAS v1
# ---------------------------------------------------------------------------


def _load_case_row(case_id: str, conn: Any) -> dict[str, Any] | None:
    """Charge la ligne cases depuis DB."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, currency, status, case_type, lot, "
            "estimated_value, procedure_type "
            "FROM public.cases WHERE id = %s",
            (case_id,),
        )
        return cur.fetchone()


def _build_case_analysis_snapshot(
    case_id: str,
    steps: list[PipelineStepResult],
    case_row: dict[str, Any],
) -> CaseAnalysisSnapshot:
    """
    Construit CAS v1 depuis les meta des steps.
    Toutes les données viennent de step.meta (unique canal — V2.2).
    Champs de décision interdits rejetés par model_validator Pydantic (INV-P7).
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


# ---------------------------------------------------------------------------
# Persist atomique (Pattern B — pas de conn.commit() ici)
# ---------------------------------------------------------------------------


def _persist_pipeline_run_and_steps(
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
) -> None:
    """
    Insère pipeline_runs + pipeline_step_runs de manière atomique.
    Pattern B : pas de conn.commit() — le context manager du router commit.
    Les violations de contrainte DB remontent volontairement (fail-fast).
    INV-P6 : pipeline_run sans steps = état interdit.
    """
    result_jsonb = json.dumps(_json_safe(cas.model_dump()) if cas else {})
    error_jsonb = "[]"

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.pipeline_runs
                (pipeline_run_id, case_id, pipeline_type, mode, status,
                 started_at, finished_at, duration_ms, triggered_by,
                 result_jsonb, error_jsonb)
            VALUES (%s, %s, 'A', 'partial', %s,
                    %s, %s, %s, %s,
                    %s::jsonb, %s::jsonb)
            """,
            (
                run_id,
                case_id,
                status,
                started_at,
                finished_at,
                duration_ms,
                triggered_by,
                result_jsonb,
                error_jsonb,
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


# ---------------------------------------------------------------------------
# Orchestrateur principal
# ---------------------------------------------------------------------------


def run_pipeline_a_partial(
    case_id: str,
    triggered_by: str,
    conn: Any,
) -> PipelineResult:
    """
    Orchestre l'exécution du pipeline A (mode partial).

    Séquence : preflight → extraction_summary → criteria_summary
               → normalization_summary → scoring → build CAS v1 → persist.

    Statuts possibles : blocked | incomplete | failed | partial_complete.
    'complete' est interdit dans #10 (réservé #14).

    Les exceptions intra-step sont structurées via _safe_step().
    Les erreurs de persistance DB restent volontairement fail-fast.
    """
    run_id = str(uuid.uuid4())
    started_at = _now()
    steps: list[PipelineStepResult] = []

    # ---- Step 1 : Preflight ------------------------------------------------
    pf_start = _now()
    pf_outcome = _safe_step("preflight", _preflight_case_a_partial, case_id, conn)
    steps.append(_to_step_result("preflight", pf_outcome, pf_start))

    if pf_outcome.status == "blocked":
        finished_at = _now()
        dur = _duration_ms(started_at, finished_at)
        _persist_pipeline_run_and_steps(
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

    # Case row chargé une seule fois (validé en preflight — existe)
    case_row = _load_case_row(case_id, conn) or {}

    # ---- Step 2 : Extraction summary ---------------------------------------
    ex_start = _now()
    ex_outcome = _safe_step(
        "extraction_summary", _load_extraction_summary, case_id, conn
    )
    steps.append(_to_step_result("extraction_summary", ex_outcome, ex_start))

    # ---- Step 3 : Criteria summary -----------------------------------------
    cr_start = _now()
    cr_outcome = _safe_step("criteria_summary", _load_criteria_summary, case_id, conn)
    steps.append(_to_step_result("criteria_summary", cr_outcome, cr_start))

    # ---- Step 4 : Normalization summary ------------------------------------
    nr_start = _now()
    nr_outcome = _safe_step(
        "normalization_summary", _load_normalization_summary, case_id, conn
    )
    steps.append(_to_step_result("normalization_summary", nr_outcome, nr_start))

    # ---- Step 5 : Scoring --------------------------------------------------
    sc_start = _now()
    sc_outcome = _safe_step("scoring", _run_scoring_step, case_id, conn)
    steps.append(_to_step_result("scoring", sc_outcome, sc_start))

    # ---- Build CAS v1 ------------------------------------------------------
    cas = _build_case_analysis_snapshot(case_id, steps, case_row)

    # ---- Déterminer statut pipeline ----------------------------------------
    step_statuses = {s.status for s in steps}
    if "failed" in step_statuses:
        pipeline_status = "failed"
    elif "blocked" in step_statuses or "incomplete" in step_statuses:
        pipeline_status = "incomplete"
    else:
        pipeline_status = "partial_complete"

    finished_at = _now()
    dur = _duration_ms(started_at, finished_at)

    # ---- Persist atomique --------------------------------------------------
    _persist_pipeline_run_and_steps(
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


# ---------------------------------------------------------------------------
# GET /last — lecture depuis result_jsonb
# ---------------------------------------------------------------------------


def get_last_pipeline_run(case_id: str, conn: Any) -> PipelineLastRunResponse | None:
    """
    Récupère le dernier run depuis pipeline_runs.result_jsonb.
    Pas de recalcul — INV-P9.
    """
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
