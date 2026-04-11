"""Assembleur d’entrées M14 à partir du workspace (ADR-V53 / M-CTO-V53-D).

Priorité :
  1. Lignes ``offer_extractions`` (données structurées existantes).
  2. Sinon ``supplier_bundles`` (``vendor_name_raw`` + ``id`` comme document_id).

Réf. faille addendum V4.2 (offers[] sans assembleur) ; le pipeline V5 consomme cette fonction.
"""

from __future__ import annotations

from typing import Any

from src.db import db_fetchall


def build_m14_offers_for_workspace(conn: Any, workspace_id: str) -> list[dict[str, Any]]:
    """Construit la liste ``offers`` pour ``M14EvaluationInput`` (workspace-scoped)."""
    rows = db_fetchall(
        conn,
        """
        SELECT bundle_id::text AS bundle_id, supplier_name,
               extracted_data_json
        FROM offer_extractions
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY created_at DESC
        """,
        {"wid": workspace_id},
    )
    offers: list[dict[str, Any]] = []
    for r in rows:
        offers.append(
            {
                "document_id": r["bundle_id"],
                "supplier_name": r.get("supplier_name"),
                "process_role": "responds_to_bid",
            }
        )
    if offers:
        return offers

    bundles = db_fetchall(
        conn,
        """
        SELECT id::text AS bundle_id, vendor_name_raw AS supplier_name
        FROM supplier_bundles
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY bundle_index ASC NULLS LAST, assembled_at ASC
        """,
        {"wid": workspace_id},
    )
    for b in bundles:
        offers.append(
            {
                "document_id": b["bundle_id"],
                "supplier_name": b.get("supplier_name"),
                "process_role": "responds_to_bid",
            }
        )
    return offers
