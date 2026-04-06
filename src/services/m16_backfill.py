"""Pont M14 → M16 : initialisation des ``criterion_assessments`` depuis ``scores_matrix``."""

from __future__ import annotations

import logging
from typing import Any

from psycopg.types.json import Json

from src.db import db_execute_one, db_fetchall, get_connection

logger = logging.getLogger(__name__)

_FORBIDDEN_KEYS = frozenset(
    {
        "winner",
        "rank",
        "recommendation",
        "be" + "st_offer",
        "selected_vendor",
        "weighted_scores",
    }
)


def initialize_criterion_assessments_from_m14(workspace_id: str) -> dict[str, Any]:
    """Lit le dernier ``evaluation_documents.scores_matrix`` et remplit ``criterion_assessments``.

    Structure : ``scores_matrix[bundle_id][criterion_key] = { ... }``.
    Idempotent : ``ON CONFLICT (workspace_id, bundle_id, criterion_key) DO NOTHING``.
    """
    inserted = 0
    skipped_unknown_bundle = 0
    skipped_existing = 0
    eval_doc_id: str | None = None

    with get_connection() as conn:
        ws = db_execute_one(
            conn,
            """
            SELECT tenant_id::text AS tenant_id
            FROM process_workspaces
            WHERE id = CAST(:wid AS uuid)
            """,
            {"wid": workspace_id},
        )
        if not ws:
            raise ValueError(f"Workspace introuvable: {workspace_id}")
        tenant_id = str(ws["tenant_id"])

        ed = db_execute_one(
            conn,
            """
            SELECT id::text AS id, scores_matrix
            FROM evaluation_documents
            WHERE workspace_id = CAST(:wid AS uuid)
            ORDER BY version DESC, created_at DESC
            LIMIT 1
            """,
            {"wid": workspace_id},
        )
        if not ed:
            logger.info(
                "m16 backfill: aucune evaluation_documents pour workspace=%s",
                workspace_id,
            )
            return {
                "workspace_id": workspace_id,
                "inserted": 0,
                "skipped_existing": 0,
                "skipped_unknown_bundle": 0,
                "evaluation_document_id": None,
            }

        eval_doc_id = ed.get("id")
        matrix = ed.get("scores_matrix")
        if not isinstance(matrix, dict):
            matrix = {}

        bundle_rows = db_fetchall(
            conn,
            """
            SELECT id::text AS id FROM supplier_bundles
            WHERE workspace_id = CAST(:wid AS uuid)
            """,
            {"wid": workspace_id},
        )
        bundle_ids = {r["id"] for r in bundle_rows}

        crit_rows = db_fetchall(
            conn,
            """
            SELECT id::text AS id FROM dao_criteria
            WHERE workspace_id = CAST(:wid AS uuid)
            """,
            {"wid": workspace_id},
        )
        dao_crit_ids = {r["id"] for r in crit_rows}

        for bundle_key, per_bundle in matrix.items():
            bid = str(bundle_key)
            if bid not in bundle_ids:
                skipped_unknown_bundle += 1
                continue
            if not isinstance(per_bundle, dict):
                continue
            for ck, cell in per_bundle.items():
                criterion_key = str(ck)
                if criterion_key in _FORBIDDEN_KEYS:
                    continue
                if not isinstance(cell, dict):
                    cell_obj: dict[str, Any] = {"value": cell}
                else:
                    cell_obj = dict(cell)
                dao_id = criterion_key if criterion_key in dao_crit_ids else None

                conn.execute(
                    """
                    INSERT INTO criterion_assessments (
                        workspace_id, tenant_id, bundle_id, criterion_key,
                        dao_criterion_id, evaluation_document_id,
                        cell_json, assessment_status, confidence
                    )
                    VALUES (
                        CAST(:workspace_id AS uuid),
                        CAST(:tenant_id AS uuid),
                        CAST(:bundle_id AS uuid),
                        :criterion_key,
                        :dao_criterion_id,
                        CAST(:evaluation_document_id AS uuid),
                        :cell_json,
                        'draft',
                        NULL
                    )
                    ON CONFLICT (workspace_id, bundle_id, criterion_key) DO NOTHING
                    RETURNING id::text AS id
                    """,
                    {
                        "workspace_id": workspace_id,
                        "tenant_id": tenant_id,
                        "bundle_id": bid,
                        "criterion_key": criterion_key,
                        "dao_criterion_id": dao_id,
                        "evaluation_document_id": eval_doc_id,
                        "cell_json": Json(cell_obj),
                    },
                )
                row = conn.fetchone()
                if row and row.get("id"):
                    inserted += 1
                else:
                    skipped_existing += 1

    return {
        "workspace_id": workspace_id,
        "inserted": inserted,
        "skipped_existing": skipped_existing,
        "skipped_unknown_bundle": skipped_unknown_bundle,
        "evaluation_document_id": eval_doc_id,
    }
