# src/couche_a/pipeline/steps.py
"""
Pipeline A individual steps — preflight, summaries, and scoring.

Pattern DB : Pattern B — each step receives conn but never commits.
"""

from __future__ import annotations

import json
from typing import Any

from src.core.models import DAOCriterion, SupplierPackage
from src.couche_a.scoring.engine import ScoringEngine

from .models import StepOutcome

RC_CASE_NOT_FOUND = "CASE_NOT_FOUND"
RC_DAO_MISSING = "DAO_MISSING"
RC_OFFERS_MISSING = "OFFERS_MISSING"
RC_MIN_OFFERS_INSUFFICIENT = "MIN_OFFERS_INSUFFICIENT"

_MIN_OFFERS_REQUIRED = 2


def preflight_case_a_partial(case_id: str, conn: Any) -> StepOutcome:
    """
    Préflight A/partial — 4 reason_codes exacts.
    """
    with conn.cursor() as cur:
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
        cur.execute(
            "SELECT COUNT(*) AS n FROM public.dao_criteria dc "
            "INNER JOIN process_workspaces pw ON pw.id = dc.workspace_id "
            "WHERE pw.legacy_case_id = %s",
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


def load_extraction_summary(case_id: str, conn: Any) -> StepOutcome:
    """Résumé des extractions disponibles dans offer_extractions."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT oe.supplier_name, oe.extracted_data_json "
            "FROM public.offer_extractions oe "
            "INNER JOIN process_workspaces pw ON pw.id = oe.workspace_id "
            "WHERE pw.legacy_case_id = %s",
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


def load_criteria_summary(case_id: str, conn: Any) -> StepOutcome:
    """Résumé des critères DAO dans dao_criteria."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT dc.categorie, dc.is_eliminatory "
            "FROM public.dao_criteria dc "
            "INNER JOIN process_workspaces pw ON pw.id = dc.workspace_id "
            "WHERE pw.legacy_case_id = %s",
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


def load_normalization_summary(case_id: str, conn: Any) -> StepOutcome:
    """Résumé de la normalisation : score_runs existants pour ce case."""
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


def run_scoring_step(
    case_id: str,
    conn: Any,
    force_recompute: bool = False,
) -> StepOutcome:
    """Délègue le scoring au ScoringEngine existant."""
    _lookup_warning: str | None = None

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

    scores = None
    eliminations: list[Any] = []

    if not force_recompute:
        try:
            cached = engine.get_latest_score_run(case_id)  # type: ignore[attr-defined]
            if cached is not None:
                scores = cached.get("scores", [])
                eliminations = cached.get("eliminations", [])
                _lookup_warning = "SCORE_REUSED_FROM_CACHE"
        except AttributeError:
            _lookup_warning = "SCORE_CACHE_UNAVAILABLE_FALLBACK"

    if scores is None:
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
    if _lookup_warning:
        meta["lookup_warning"] = _lookup_warning

    return StepOutcome(
        status="ok" if scores else "incomplete",
        reason_code=None if scores else "NO_SCORES_COMPUTED",
        reason_message=(
            None if scores else f"Aucun score calculé pour case_id={case_id!r}"
        ),
        meta=meta,
    )
