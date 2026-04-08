# src/couche_a/pipeline/steps.py
"""
Pipeline A individual steps — preflight, summaries.

Pattern DB : Pattern B — each step receives conn but never commits.
Scoring helpers live in service.py for monkeypatch compatibility.
"""

from __future__ import annotations

from typing import Any

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
