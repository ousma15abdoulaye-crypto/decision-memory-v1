"""Lecture cohérente du dernier ``evaluation_documents`` par workspace.

ADR-0017 P5 : un ordre de tri unique pour « le dernier document d'évaluation »
(évite les divergences entre frame UI, projection PV et bridge M14→M16).
"""

from __future__ import annotations

from typing import Any

from src.db import db_execute_one

# Clause partagée — garder aligné avec ``m14_evaluation_repository.get_latest`` (version)
# + tie-break ``created_at`` pour lignes même version.
LATEST_EVALUATION_DOCUMENT_ORDER_CLAUSE = (
    "ORDER BY version DESC NULLS LAST, created_at DESC NULLS LAST"
)


def fetch_latest_evaluation_document_for_workspace(
    conn: Any,
    workspace_id: str,
    *,
    columns: str = "id::text AS id, scores_matrix, created_at, version",
) -> dict[str, Any] | None:
    """Dernière ligne ``evaluation_documents`` pour le workspace.

    ``columns`` permet de restreindre le SELECT (ex. ``scores_matrix`` seul)
    tout en conservant le même ORDER BY. Réservé aux **littéraux internes**
    figés dans le code (pas d'entrée utilisateur).
    """
    return db_execute_one(
        conn,
        f"""
        SELECT {columns}
        FROM evaluation_documents
        WHERE workspace_id = CAST(:ws AS uuid)
        {LATEST_EVALUATION_DOCUMENT_ORDER_CLAUSE}
        LIMIT 1
        """,
        {"ws": workspace_id},
    )
