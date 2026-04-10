"""Requêtes métier M16 — domaines, assessments, cadre par cible."""

from __future__ import annotations

from typing import Any

from src.db import db_execute_one, db_fetchall


def count_criterion_assessments(
    conn: Any, workspace_id: str, bundle_id: str | None
) -> int:
    if bundle_id:
        row = db_execute_one(
            conn,
            """
            SELECT COUNT(*)::int AS n
            FROM criterion_assessments
            WHERE workspace_id = CAST(:wid AS uuid)
              AND bundle_id = CAST(:bid AS uuid)
            """,
            {"wid": workspace_id, "bid": bundle_id},
        )
    else:
        row = db_execute_one(
            conn,
            """
            SELECT COUNT(*)::int AS n
            FROM criterion_assessments
            WHERE workspace_id = CAST(:wid AS uuid)
            """,
            {"wid": workspace_id},
        )
    return int(row["n"]) if row and row.get("n") is not None else 0


def list_criterion_assessments_paged(
    conn: Any,
    workspace_id: str,
    bundle_id: str | None,
    *,
    limit: int,
    offset: int,
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
            LIMIT :lim OFFSET :off
            """,
            {"wid": workspace_id, "bid": bundle_id, "lim": limit, "off": offset},
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
        LIMIT :lim OFFSET :off
        """,
        {"wid": workspace_id, "lim": limit, "off": offset},
    )


def count_evaluation_domains(conn: Any, workspace_id: str) -> int:
    row = db_execute_one(
        conn,
        """
        SELECT COUNT(*)::int AS n
        FROM evaluation_domains
        WHERE workspace_id = CAST(:wid AS uuid)
        """,
        {"wid": workspace_id},
    )
    return int(row["n"]) if row and row.get("n") is not None else 0


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


def list_evaluation_domains_paged(
    conn: Any, workspace_id: str, *, limit: int, offset: int
) -> list[dict[str, Any]]:
    return db_fetchall(
        conn,
        """
        SELECT id::text AS id, workspace_id::text AS workspace_id,
               code, label, display_order
        FROM evaluation_domains
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY display_order, code
        LIMIT :lim OFFSET :off
        """,
        {"wid": workspace_id, "lim": limit, "off": offset},
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
        SELECT id::text AS id,
               price_line_id::text AS price_line_id,
               bundle_id::text AS bundle_id,
               amount::text AS amount,
               currency,
               market_delta_pct::text AS market_delta_pct,
               market_delta_computed_at
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


def count_clarification_requests(
    conn: Any, workspace_id: str, status: str | None
) -> int:
    if status:
        row = db_execute_one(
            conn,
            """
            SELECT COUNT(*)::int AS n
            FROM clarification_requests
            WHERE workspace_id = CAST(:wid AS uuid)
              AND status = :st
            """,
            {"wid": workspace_id, "st": status},
        )
    else:
        row = db_execute_one(
            conn,
            """
            SELECT COUNT(*)::int AS n
            FROM clarification_requests
            WHERE workspace_id = CAST(:wid AS uuid)
            """,
            {"wid": workspace_id},
        )
    return int(row["n"]) if row and row.get("n") is not None else 0


def list_clarification_requests_paged(
    conn: Any,
    workspace_id: str,
    status: str | None,
    *,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    if status:
        return db_fetchall(
            conn,
            """
            SELECT id::text AS id, workspace_id::text AS workspace_id,
                   criterion_assessment_id::text AS criterion_assessment_id,
                   status, requested_by, created_at, resolved_at
            FROM clarification_requests
            WHERE workspace_id = CAST(:wid AS uuid)
              AND status = :st
            ORDER BY created_at DESC
            LIMIT :lim OFFSET :off
            """,
            {"wid": workspace_id, "st": status, "lim": limit, "off": offset},
        )
    return db_fetchall(
        conn,
        """
        SELECT id::text AS id, workspace_id::text AS workspace_id,
               criterion_assessment_id::text AS criterion_assessment_id,
               status, requested_by, created_at, resolved_at
        FROM clarification_requests
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY created_at DESC
        LIMIT :lim OFFSET :off
        """,
        {"wid": workspace_id, "lim": limit, "off": offset},
    )


def count_validated_notes(conn: Any, workspace_id: str) -> int:
    row = db_execute_one(
        conn,
        """
        SELECT COUNT(*)::int AS n
        FROM validated_analytical_notes
        WHERE workspace_id = CAST(:wid AS uuid)
        """,
        {"wid": workspace_id},
    )
    return int(row["n"]) if row and row.get("n") is not None else 0


def list_validated_notes_paged(
    conn: Any, workspace_id: str, *, limit: int, offset: int
) -> list[dict[str, Any]]:
    return db_fetchall(
        conn,
        """
        SELECT id::text AS id, workspace_id::text AS workspace_id,
               criterion_assessment_id::text AS criterion_assessment_id,
               source_message_id::text AS source_message_id,
               note_body, validated_by, validated_at
        FROM validated_analytical_notes
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY validated_at DESC
        LIMIT :lim OFFSET :off
        """,
        {"wid": workspace_id, "lim": limit, "off": offset},
    )


def list_validated_notes_for_assessment(
    conn: Any, workspace_id: str, criterion_assessment_id: str
) -> list[dict[str, Any]]:
    return db_fetchall(
        conn,
        """
        SELECT id::text AS id, workspace_id::text AS workspace_id,
               criterion_assessment_id::text AS criterion_assessment_id,
               source_message_id::text AS source_message_id,
               note_body, validated_by, validated_at
        FROM validated_analytical_notes
        WHERE workspace_id = CAST(:wid AS uuid)
          AND criterion_assessment_id = CAST(:ca AS uuid)
        ORDER BY validated_at DESC
        """,
        {"wid": workspace_id, "ca": criterion_assessment_id},
    )


def count_assessment_history(conn: Any, assessment_id: str) -> int:
    row = db_execute_one(
        conn,
        """
        SELECT COUNT(*)::int AS n
        FROM criterion_assessment_history
        WHERE criterion_assessment_id = CAST(:aid AS uuid)
        """,
        {"aid": assessment_id},
    )
    return int(row["n"]) if row and row.get("n") is not None else 0


def list_assessment_history_paged(
    conn: Any, assessment_id: str, *, limit: int, offset: int
) -> list[dict[str, Any]]:
    return db_fetchall(
        conn,
        """
        SELECT id, criterion_assessment_id::text AS criterion_assessment_id,
               workspace_id::text AS workspace_id,
               changed_at, actor_id, old_status, new_status, payload
        FROM criterion_assessment_history
        WHERE criterion_assessment_id = CAST(:aid AS uuid)
        ORDER BY changed_at, id
        LIMIT :lim OFFSET :off
        """,
        {"aid": assessment_id, "lim": limit, "off": offset},
    )
