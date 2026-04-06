"""Modèle tableau comparatif — projection serveur uniquement (pas de gagnant)."""

from __future__ import annotations

from typing import Any

from src.db import get_connection
from src.services.pv_builder import build_evaluation_projection

COMPARATIVE_MODEL_VERSION = "1.0"


def build_comparative_table_model(workspace_id: str) -> dict[str, Any]:
    """Projection depuis l’état DB courant (critères, bundles, scores sanitisés).

    Ne remplace pas le snapshot scellé pour les exports PV : utiliser
    :func:`build_comparative_table_model_from_snapshot` pour tout rendu
    après seal.
    """
    with get_connection() as conn:
        ev = build_evaluation_projection(conn, workspace_id)
    return {
        "workspace_id": workspace_id,
        "comparative_model_version": COMPARATIVE_MODEL_VERSION,
        "source": "live_db",
        "criteria": ev["criteria"],
        "bundles": ev["bundles"],
        "scores_matrix": ev["scores_matrix"],
    }


def build_comparative_table_model_from_snapshot(
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Tableau comparatif dérivé **uniquement** du ``pv_snapshot`` scellé.

    Aucun recalcul métier : extraction + structure pour rendu XLSX/PDF.
    """
    proc = snapshot.get("process") or {}
    ev = snapshot.get("evaluation") or {}
    meta = snapshot.get("meta") or {}
    return {
        "workspace_id": proc.get("workspace_id"),
        "comparative_model_version": COMPARATIVE_MODEL_VERSION,
        "source": "pv_snapshot_sealed",
        "criteria": ev.get("criteria") or [],
        "bundles": ev.get("bundles") or [],
        "scores_matrix": ev.get("scores_matrix") or {},
        "trace": {
            "snapshot_schema_version": meta.get("snapshot_schema_version"),
            "render_template_version": meta.get("render_template_version"),
            "generated_from_session_id": meta.get("generated_from_session_id"),
        },
    }
