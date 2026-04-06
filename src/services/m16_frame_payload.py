"""Enrichissement cadre M16 — signaux, contributions pondérées (F6–F7)."""

from __future__ import annotations

from typing import Any

from src.db import db_fetchall
from src.services.signal_engine import (
    _numeric_from_cell,
    signal_for_criterion_assessment_row,
)
from src.services.weight_validator import (
    criteria_weight_by_id,
    validate_criteria_weights,
)


def enrich_assessments_for_frame(
    conn: Any,
    workspace_id: str,
    assessments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, float | None], dict[str, Any]]:
    """Retourne (assessments enrichis, bundle_weighted_totals, weight_validation)."""
    wval = validate_criteria_weights(conn, workspace_id)
    w_by_cid = criteria_weight_by_id(conn, workspace_id)

    bundle_rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id, qualification_status
        FROM supplier_bundles
        WHERE workspace_id = CAST(:ws AS uuid)
        """,
        {"ws": workspace_id},
    )
    bundle_eliminated = {
        str(b["id"]): str(b.get("qualification_status") or "") == "disqualified"
        for b in bundle_rows
    }

    enriched: list[dict[str, Any]] = []
    bundle_totals: dict[str, float] = {}
    bundle_has_score: dict[str, bool] = {}

    for r in assessments:
        cj = r.get("cell_json")
        if not isinstance(cj, dict):
            cj = {}
        dao_id = r.get("dao_criterion_id")
        w_pct, is_elim = (0.0, False)
        if dao_id and str(dao_id) in w_by_cid:
            w_pct, is_elim = w_by_cid[str(dao_id)]
        score = _numeric_from_cell(cj)
        contrib: float | None = None
        if score is not None and not is_elim and w_pct:
            contrib = round(float(score) * float(w_pct) / 100.0, 4)

        sig = signal_for_criterion_assessment_row(r, open_clarifications=0)

        bid = str(r.get("bundle_id") or "")
        if bid:
            bundle_has_score.setdefault(bid, False)
            if contrib is not None:
                bundle_totals[bid] = bundle_totals.get(bid, 0.0) + contrib
                bundle_has_score[bid] = True

        row_out = dict(r)
        row_out["computed_weighted_contribution"] = contrib
        row_out["signal"] = sig
        enriched.append(row_out)

    bundle_weighted_totals: dict[str, float | None] = {}
    all_bundles = {str(x.get("bundle_id")) for x in assessments if x.get("bundle_id")}
    for bid in all_bundles:
        if bundle_eliminated.get(bid):
            bundle_weighted_totals[bid] = None
        elif bundle_has_score.get(bid):
            bundle_weighted_totals[bid] = round(bundle_totals.get(bid, 0.0), 2)
        else:
            bundle_weighted_totals[bid] = None

    return enriched, bundle_weighted_totals, wval
