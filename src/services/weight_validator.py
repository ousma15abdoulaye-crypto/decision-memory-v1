"""INV-W03 — somme des poids pondérés = 100 % (hors éliminatoires à poids 0)."""

from __future__ import annotations

from typing import Any

from src.db import db_fetchall


def validate_criteria_weights(conn: Any, workspace_id: str) -> dict[str, Any]:
    rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id, name, critere_nom,
               weight, ponderation,
               is_eliminatory, seuil_elimination
        FROM dao_criteria
        WHERE workspace_id = CAST(:ws AS uuid)
        ORDER BY created_at NULLS LAST, id
        """,
        {"ws": workspace_id},
    )

    errors: list[str] = []
    eliminatory_with_weight: list[dict[str, Any]] = []
    weighted_sum = 0.0

    for c in rows:
        w_raw = c.get("weight")
        if w_raw is None:
            w_raw = c.get("ponderation")
        w = float(w_raw) if w_raw is not None else 0.0

        is_elim = bool(
            c.get("is_eliminatory")
            if c.get("is_eliminatory") is not None
            else c.get("seuil_elimination") is not None
        )
        name = str(c.get("name") or c.get("critere_nom") or c.get("id") or "?")

        if is_elim and w > 0.0:
            eliminatory_with_weight.append(
                {"id": str(c.get("id")), "name": name, "weight": w}
            )
            errors.append(
                f"Critère éliminatoire {name!r} a un poids {w} — doit être 0."
            )

        if not is_elim:
            weighted_sum += w

    if rows and abs(weighted_sum - 100.0) > 0.01:
        errors.append(
            f"Somme des poids pondérés = {weighted_sum:.2f} % — attendu 100.00 %."
        )

    return {
        "valid": len(errors) == 0,
        "weighted_sum": round(weighted_sum, 2),
        "criteria_count": len(rows),
        "eliminatory_with_weight": eliminatory_with_weight,
        "errors": errors,
    }


def criteria_weight_by_id(
    conn: Any, workspace_id: str
) -> dict[str, tuple[float, bool]]:
    """dao_criterion_id -> (weight_pct, is_eliminatory)."""
    rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id,
               weight, ponderation,
               is_eliminatory, seuil_elimination
        FROM dao_criteria
        WHERE workspace_id = CAST(:ws AS uuid)
        """,
        {"ws": workspace_id},
    )
    out: dict[str, tuple[float, bool]] = {}
    for c in rows:
        w_raw = c.get("weight")
        if w_raw is None:
            w_raw = c.get("ponderation")
        w = float(w_raw) if w_raw is not None else 0.0
        is_elim = bool(
            c.get("is_eliminatory")
            if c.get("is_eliminatory") is not None
            else c.get("seuil_elimination") is not None
        )
        out[str(c["id"])] = (w, is_elim)
    return out
