"""Tests DB integrity — no_winner_field CHECK constraint (INV-W06, REGLE-09, S5).

Vérifie :
- INSERT evaluation_documents avec payload winner -> rejeté CHECK
- INSERT evaluation_documents avec payload rank -> rejeté CHECK
- INSERT evaluation_documents avec payload scores standard -> OK
- INSERT evaluation_documents avec scores_matrix NULL -> OK

Pré-condition : migrations 068-073 appliquées (workspace_id + CHECK constraint).
"""

from __future__ import annotations

import json
import uuid

import psycopg
import pytest


def _make_case_and_workspace(cur) -> tuple[str, str, str, int]:
    """Retourne (case_id, ws_id, tenant_id, user_id)."""
    cur.execute("SELECT set_config('app.is_admin', 'true', true)")

    cur.execute("SELECT id FROM cases LIMIT 1")
    row = cur.fetchone()
    if row:
        case_id = str(row["id"])
    else:
        case_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO cases (id, case_type, title, created_at, status, tenant_id)
            VALUES (%s, 'DAO', 'Test Case', NOW()::TEXT, 'open', 'test')
            """,
            (case_id,),
        )

    cur.execute("SELECT id FROM tenants WHERE code = 'sci_mali' LIMIT 1")
    row = cur.fetchone()
    tenant_id = str(row["id"]) if row else str(uuid.uuid4())
    if not row:
        cur.execute(
            "INSERT INTO tenants (id, code, name) VALUES (%s, 'sci_mali', 'SCI Mali')",
            (tenant_id,),
        )

    cur.execute("SELECT id FROM users LIMIT 1")
    row = cur.fetchone()
    user_id = int(row["id"]) if row else 1

    ws_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO process_workspaces
            (id, tenant_id, created_by, reference_code, title, process_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (ws_id, tenant_id, user_id, f"WIN-{ws_id[:8]}", "Winner Test", "devis_formel"),
    )
    return case_id, ws_id, tenant_id, user_id


def _insert_eval_doc(cur, case_id: str, ws_id: str, scores_matrix) -> None:
    cur.execute(
        """
        INSERT INTO evaluation_documents
            (id, case_id, workspace_id, scores_matrix)
        VALUES (%s, %s, %s, %s)
        """,
        (str(uuid.uuid4()), case_id, ws_id, json.dumps(scores_matrix)),
    )


@pytest.mark.db_integrity
def test_no_winner_in_scores_matrix_rejected(db_conn):
    """scores_matrix avec clé 'winner' doit être rejeté par le CHECK."""
    with db_conn.cursor() as cur:
        case_id, ws_id, _, _ = _make_case_and_workspace(cur)
        with pytest.raises(psycopg.errors.CheckViolation):
            _insert_eval_doc(
                cur, case_id, ws_id, {"winner": "SARL KONARE", "scores": {}}
            )


@pytest.mark.db_integrity
def test_no_rank_in_scores_matrix_rejected(db_conn):
    """scores_matrix avec clé 'rank' doit être rejeté par le CHECK."""
    with db_conn.cursor() as cur:
        case_id, ws_id, _, _ = _make_case_and_workspace(cur)
        with pytest.raises(psycopg.errors.CheckViolation):
            _insert_eval_doc(cur, case_id, ws_id, {"rank": [1, 2, 3], "scores": {}})


@pytest.mark.db_integrity
def test_no_recommendation_in_scores_matrix_rejected(db_conn):
    """scores_matrix avec clé 'recommendation' doit être rejeté."""
    with db_conn.cursor() as cur:
        case_id, ws_id, _, _ = _make_case_and_workspace(cur)
        with pytest.raises(psycopg.errors.CheckViolation):
            _insert_eval_doc(
                cur, case_id, ws_id, {"recommendation": "choisir A", "scores": {}}
            )


@pytest.mark.db_integrity
def test_scores_without_winner_ok(db_conn):
    """scores_matrix valide (sans winner/rank) doit être accepté."""
    with db_conn.cursor() as cur:
        case_id, ws_id, _, _ = _make_case_and_workspace(cur)
        _insert_eval_doc(
            cur,
            case_id,
            ws_id,
            {
                "scores": {
                    "SARL KONARE": {"technique": 75, "prix": 80},
                    "ETS DIALLO": {"technique": 68, "prix": 85},
                }
            },
        )
        cur.execute(
            "SELECT id FROM evaluation_documents WHERE workspace_id = %s LIMIT 1",
            (ws_id,),
        )
        assert cur.fetchone() is not None


@pytest.mark.db_integrity
def test_scores_matrix_null_ok(db_conn):
    """scores_matrix NULL doit être accepté."""
    with db_conn.cursor() as cur:
        case_id, ws_id, _, _ = _make_case_and_workspace(cur)
        cur.execute(
            """
            INSERT INTO evaluation_documents
                (id, case_id, workspace_id, scores_matrix)
            VALUES (%s, %s, %s, NULL)
            """,
            (str(uuid.uuid4()), case_id, ws_id),
        )
        cur.execute(
            "SELECT scores_matrix FROM evaluation_documents WHERE workspace_id = %s LIMIT 1",
            (ws_id,),
        )
        row = cur.fetchone()
        assert row is not None
        assert row["scores_matrix"] is None
