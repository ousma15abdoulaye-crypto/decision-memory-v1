"""L1 — score_runs append-only (DB-level, trigger-backed).

ADR-0006 / INV-6
Trigger  : trg_score_runs_append_only (BEFORE UPDATE OR DELETE)
Exception: 'append-only: update/delete forbidden on score_runs'

Pattern  : db_conn (autocommit=True, conftest racine).
           INSERT est auto-commité — reste dans score_runs (append-only by design).
           UPDATE/DELETE → trigger BEFORE → psycopg.Error → rollback défensif.
           Zéro DELETE de cleanup sur score_runs.
"""

import uuid

import psycopg
import pytest

_TRIGGER_NAME = "trg_score_runs_append_only"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trigger_present(db_conn) -> bool:
    """Vérifie que le trigger UPDATE + DELETE est présent (2 entrées)."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS n
            FROM information_schema.triggers
            WHERE trigger_schema = 'public'
              AND event_object_table = 'score_runs'
              AND trigger_name = %s
              AND event_manipulation IN ('UPDATE', 'DELETE')
            """,
            (_TRIGGER_NAME,),
        )
        return cur.fetchone()["n"] >= 2


def _insert_run(
    db_conn,
    case_id: str,
    supplier: str = "S-TEST",
    category: str = "total",
    score: float = 75.0,
) -> str:
    """INSERT dans score_runs. Retourne l'UUID du run (auto-commité)."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.score_runs (case_id, supplier_name, category, score_value)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (case_id, supplier, category, score),
        )
        return str(cur.fetchone()["id"])


# ---------------------------------------------------------------------------
# L1a — UPDATE interdit
# ---------------------------------------------------------------------------


def test_l1a_update_forbidden(db_conn):
    """UPDATE sur score_runs lève psycopg.Error 'append-only' (trigger BEFORE UPDATE)."""
    if not _trigger_present(db_conn):
        pytest.skip(
            f"Trigger {_TRIGGER_NAME!r} absent — signal CTO : append-only non garanti DB-level"
        )

    case_id = str(uuid.uuid4())
    run_id = _insert_run(db_conn, case_id)

    with pytest.raises(psycopg.Error) as exc:
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE public.score_runs SET score_value = 1.0 WHERE id = %s",
                (run_id,),
            )

    assert (
        "append-only" in str(exc.value).lower()
    ), f"Message inattendu du trigger : {exc.value!r}"
    db_conn.rollback()


# ---------------------------------------------------------------------------
# L1b — DELETE interdit
# ---------------------------------------------------------------------------


def test_l1b_delete_forbidden(db_conn):
    """DELETE sur score_runs lève psycopg.Error 'append-only' (trigger BEFORE DELETE)."""
    if not _trigger_present(db_conn):
        pytest.skip(
            f"Trigger {_TRIGGER_NAME!r} absent — signal CTO : append-only non garanti DB-level"
        )

    case_id = str(uuid.uuid4())
    run_id = _insert_run(db_conn, case_id)

    with pytest.raises(psycopg.Error) as exc:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.score_runs WHERE id = %s",
                (run_id,),
            )

    assert (
        "append-only" in str(exc.value).lower()
    ), f"Message inattendu du trigger : {exc.value!r}"
    db_conn.rollback()


# ---------------------------------------------------------------------------
# L1c — double INSERT autorisé (accumulation append-only)
# ---------------------------------------------------------------------------


def test_l1c_double_insert_allowed(db_conn):
    """2 INSERTs successifs sur le même (case_id, supplier, category) → 2 lignes distinctes."""
    case_id = str(uuid.uuid4())

    id1 = _insert_run(db_conn, case_id, supplier="ACME", category="total", score=80.0)
    id2 = _insert_run(db_conn, case_id, supplier="ACME", category="total", score=90.0)

    assert id1 != id2, "Les deux INSERTs doivent produire des IDs distincts"

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM public.score_runs WHERE case_id = %s",
            (case_id,),
        )
        n = cur.fetchone()["n"]

    assert n >= 2, f"Attendu >= 2 lignes pour case_id={case_id}, obtenu {n}"
