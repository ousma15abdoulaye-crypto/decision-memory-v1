"""Matrice comparative produit (UI) — ADR-0017 / CONTEXT_ANCHOR.

``GET /comparative-matrix`` : base evaluation-frame ; ``source=m16`` si
``criterion_assessments`` non vide (overlay), sinon ``m14``. Ce n'est pas la
projection exports XLSX/PDF (voir ``build_evaluation_projection`` /
``GET …/m16/comparative-table-model``).
"""

from __future__ import annotations

from typing import Any

from src.db import db_execute_one, db_fetchall
from src.models.m16_enums import PriceSignal
from src.services.m16_evaluation_service import list_criterion_assessments
from src.services.m16_frame_payload import enrich_assessments_for_frame
from src.services.signal_engine import _numeric_from_cell
from src.services.workspace_evaluation_frame_assembly import (
    build_evaluation_frame_payload,
)


def workspace_has_m16_assessments(conn: Any, workspace_id: str) -> bool:
    row = db_execute_one(
        conn,
        """
        SELECT 1 AS ok
        FROM criterion_assessments
        WHERE workspace_id = CAST(:ws AS uuid)
        LIMIT 1
        """,
        {"ws": workspace_id},
    )
    return bool(row)


def _ui_signal(sig: str) -> str:
    if sig == PriceSignal.bell.value:
        return PriceSignal.yellow.value
    return sig


def _build_m16_matrix_overlay(conn: Any, workspace_id: str) -> dict[str, Any]:
    assessments_raw = list_criterion_assessments(conn, workspace_id, bundle_id=None)
    enriched, bundle_weighted_totals, _wval = enrich_assessments_for_frame(
        conn, workspace_id, assessments_raw
    )

    scores_matrix: dict[str, dict[str, dict[str, Any]]] = {}
    for r in enriched:
        bid = str(r.get("bundle_id") or "")
        cid = str(r.get("dao_criterion_id") or "")
        if not bid or not cid:
            continue
        cj = r.get("cell_json")
        if not isinstance(cj, dict):
            cj = {}
        score = _numeric_from_cell(cj)
        if score is None:
            score = 0.0
        conf = r.get("confidence")
        try:
            conf_f = float(conf) if conf is not None else 0.6
        except (TypeError, ValueError):
            conf_f = 0.6
        sig = _ui_signal(str(r.get("signal") or "yellow"))
        scores_matrix.setdefault(bid, {})[cid] = {
            "score": float(score),
            "confidence": conf_f,
            "signal": sig,
        }

    dao_crit_rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id, critere_nom, ponderation,
               is_eliminatory, seuil_elimination
        FROM dao_criteria
        WHERE workspace_id = :ws
        ORDER BY created_at NULLS LAST, id
        """,
        {"ws": workspace_id},
    )
    criteria = [
        {
            "id": r["id"],
            "critere_nom": r.get("critere_nom"),
            "ponderation": (
                float(r["ponderation"]) if r.get("ponderation") is not None else 0
            ),
            "is_eliminatory": bool(r.get("is_eliminatory")),
        }
        for r in dao_crit_rows
    ]

    sb_rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id, vendor_name_raw
        FROM supplier_bundles
        WHERE workspace_id = :ws
        ORDER BY bundle_index NULLS LAST, id
        """,
        {"ws": workspace_id},
    )
    suppliers = [
        {
            "id": r["id"],
            "name": (r.get("vendor_name_raw") or r["id"] or "")[:500],
        }
        for r in sb_rows
    ]

    weighted: dict[str, float | None] = {}
    for k, v in bundle_weighted_totals.items():
        weighted[k] = float(v) if v is not None else None

    return {
        "scores_matrix": scores_matrix,
        "criteria": criteria,
        "suppliers": suppliers,
        "weighted_totals": weighted,
    }


def build_comparative_matrix_payload(conn: Any, workspace_id: str) -> dict[str, Any]:
    """Payload stable pour l’UI : même enveloppe que evaluation-frame + source."""
    base = build_evaluation_frame_payload(conn, workspace_id)
    if not base:
        return {}

    if workspace_has_m16_assessments(conn, workspace_id):
        overlay = _build_m16_matrix_overlay(conn, workspace_id)
        base["scores_matrix"] = overlay["scores_matrix"]
        base["criteria"] = overlay["criteria"]
        base["suppliers"] = overlay["suppliers"]
        base["weighted_totals"] = overlay["weighted_totals"]
        base["source"] = "m16"
    else:
        base["source"] = "m14"

    base["schema_version"] = "comparative_matrix_v1"
    return base
