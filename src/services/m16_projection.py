"""Projection M16 — domaines, assessments, prix pour PV et comparatif."""

from __future__ import annotations

from typing import Any

from src.db import db_fetchall


def fetch_m16_evaluation_extras(conn: Any, workspace_id: str) -> dict[str, Any]:
    """Charge les données M16 relationnelles pour un workspace (hors scores_matrix)."""
    domains_rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id, code, label, display_order
        FROM evaluation_domains
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY display_order, code
        """,
        {"wid": workspace_id},
    )
    domains = [
        {
            "id": r["id"],
            "code": r.get("code"),
            "label": r.get("label"),
            "display_order": int(r.get("display_order") or 0),
        }
        for r in domains_rows
    ]

    ca_rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id, bundle_id::text AS bundle_id, criterion_key,
               dao_criterion_id, assessment_status,
               confidence::float AS confidence, cell_json
        FROM criterion_assessments
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY bundle_id, criterion_key
        """,
        {"wid": workspace_id},
    )
    assessments: list[dict[str, Any]] = []
    for r in ca_rows:
        cj = r.get("cell_json")
        if not isinstance(cj, dict):
            cj = {}
        assessments.append(
            {
                "id": r["id"],
                "bundle_id": r["bundle_id"],
                "criterion_key": r.get("criterion_key"),
                "dao_criterion_id": r.get("dao_criterion_id"),
                "assessment_status": r.get("assessment_status"),
                "confidence": r.get("confidence"),
                "cell_json": cj,
            }
        )

    plc_rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id, line_code, label, unit
        FROM price_line_comparisons
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY line_code
        """,
        {"wid": workspace_id},
    )
    price_lines = [
        {
            "id": r["id"],
            "line_code": r.get("line_code"),
            "label": r.get("label"),
            "unit": r.get("unit"),
        }
        for r in plc_rows
    ]

    plbv_rows = db_fetchall(
        conn,
        """
        SELECT p.id::text AS id, p.price_line_id::text AS price_line_id,
               p.bundle_id::text AS bundle_id,
               p.amount::text AS amount, p.currency
        FROM price_line_bundle_values p
        WHERE p.workspace_id = CAST(:wid AS uuid)
        ORDER BY p.price_line_id, p.bundle_id
        """,
        {"wid": workspace_id},
    )
    price_values = [dict(r) for r in plbv_rows]

    return {
        "domains": domains,
        "assessments": assessments,
        "price_lines": price_lines,
        "price_values": price_values,
    }
