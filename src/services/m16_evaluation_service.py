"""Requêtes métier M16 — domaines, assessments, cadre par cible."""

from __future__ import annotations

from typing import Any

from src.db import db_execute_one, db_fetchall


def list_evaluation_domains(conn: Any, workspace_id: str) -> list[dict[str, Any]]:
    return db_fetchall(
        conn,
        """
        SELECT id::text AS id, workspace_id::text AS workspace_id,
               code, label, display_order
        FROM evaluation_domains
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY display_order, code
        """,
        {"wid": workspace_id},
    )


def list_criterion_assessments(
    conn: Any, workspace_id: str, bundle_id: str | None = None
) -> list[dict[str, Any]]:
    if bundle_id:
        return db_fetchall(
            conn,
            """
            SELECT id::text AS id, workspace_id::text AS workspace_id,
                   bundle_id::text AS bundle_id, criterion_key,
                   dao_criterion_id, evaluation_document_id::text AS evaluation_document_id,
                   cell_json, assessment_status,
                   confidence::float AS confidence
            FROM criterion_assessments
            WHERE workspace_id = CAST(:wid AS uuid)
              AND bundle_id = CAST(:bid AS uuid)
            ORDER BY criterion_key
            """,
            {"wid": workspace_id, "bid": bundle_id},
        )
    return db_fetchall(
        conn,
        """
        SELECT id::text AS id, workspace_id::text AS workspace_id,
               bundle_id::text AS bundle_id, criterion_key,
               dao_criterion_id, evaluation_document_id::text AS evaluation_document_id,
               cell_json, assessment_status,
               confidence::float AS confidence
        FROM criterion_assessments
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY bundle_id, criterion_key
        """,
        {"wid": workspace_id},
    )


def list_price_lines(conn: Any, workspace_id: str) -> list[dict[str, Any]]:
    return db_fetchall(
        conn,
        """
        SELECT id::text AS id, line_code, label, unit
        FROM price_line_comparisons
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY line_code
        """,
        {"wid": workspace_id},
    )


def list_price_bundle_values(conn: Any, workspace_id: str) -> list[dict[str, Any]]:
    return db_fetchall(
        conn,
        """
        SELECT id::text AS id, price_line_id::text AS price_line_id,
               bundle_id::text AS bundle_id,
               amount::text AS amount, currency
        FROM price_line_bundle_values
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY price_line_id, bundle_id
        """,
        {"wid": workspace_id},
    )


def resolve_workspace_tenant(conn: Any, workspace_id: str) -> dict[str, Any] | None:
    return db_execute_one(
        conn,
        """
        SELECT id::text AS id, tenant_id::text AS tenant_id
        FROM process_workspaces
        WHERE id = CAST(:wid AS uuid)
        """,
        {"wid": workspace_id},
    )
