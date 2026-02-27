"""L13 — pipeline_runs + pipeline_step_runs append-only (DB-level, trigger-backed).

ADR-0012 / INV-P4
Triggers : trg_pipeline_runs_append_only (BEFORE UPDATE OR DELETE)
           trg_pipeline_step_runs_append_only (BEFORE UPDATE OR DELETE)

Pattern  : db_conn (autocommit=True, conftest racine).
           INSERT est auto-commité — reste dans pipeline_runs (append-only by design).
           UPDATE/DELETE → trigger BEFORE → psycopg.Error → rollback défensif.
           Zéro DELETE de cleanup sur pipeline_runs / pipeline_step_runs.
"""

from __future__ import annotations

import psycopg
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trigger_present(db_conn, table: str, trigger_name: str) -> bool:
    """Vérifie que le trigger UPDATE + DELETE est présent (2 entrées)."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS n
            FROM information_schema.triggers
            WHERE trigger_schema = 'public'
              AND event_object_table = %s
              AND trigger_name = %s
              AND event_manipulation IN ('UPDATE', 'DELETE')
            """,
            (table, trigger_name),
        )
        return cur.fetchone()["n"] >= 2


def _insert_pipeline_run(db_conn, case_id: str) -> str:
    """INSERT dans pipeline_runs. Retourne pipeline_run_id (auto-commité)."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.pipeline_runs
                (case_id, pipeline_type, mode, status, triggered_by,
                 result_jsonb, error_jsonb)
            VALUES (%s, 'A', 'partial', 'blocked', 'test-runner',
                    '{}'::jsonb, '[]'::jsonb)
            RETURNING pipeline_run_id
            """,
            (case_id,),
        )
        return str(cur.fetchone()["pipeline_run_id"])


def _insert_pipeline_step_run(db_conn, pipeline_run_id: str) -> str:
    """INSERT dans pipeline_step_runs. Retourne step_run_id (auto-commité)."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.pipeline_step_runs
                (pipeline_run_id, step_name, status)
            VALUES (%s, 'preflight', 'blocked')
            RETURNING step_run_id
            """,
            (pipeline_run_id,),
        )
        return str(cur.fetchone()["step_run_id"])


# ---------------------------------------------------------------------------
# pipeline_runs — trigger présent
# ---------------------------------------------------------------------------


def test_pr_trigger_present(db_conn):
    """Trigger trg_pipeline_runs_append_only est enregistré pour UPDATE et DELETE."""
    if not _trigger_present(db_conn, "pipeline_runs", "trg_pipeline_runs_append_only"):
        pytest.fail(
            "trg_pipeline_runs_append_only absent — "
            "migration 032 non appliquée ou trigger manquant"
        )


# ---------------------------------------------------------------------------
# pipeline_runs — UPDATE interdit
# ---------------------------------------------------------------------------


def test_pr_update_forbidden(db_conn, case_factory):
    """UPDATE sur pipeline_runs lève psycopg.Error 'append-only' (trigger BEFORE UPDATE)."""
    if not _trigger_present(db_conn, "pipeline_runs", "trg_pipeline_runs_append_only"):
        pytest.skip("Trigger absent — test non pertinent")

    case_id = case_factory()
    run_id = _insert_pipeline_run(db_conn, case_id)

    with pytest.raises(psycopg.Error) as exc:
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE public.pipeline_runs SET status = 'failed' "
                "WHERE pipeline_run_id = %s",
                (run_id,),
            )

    assert (
        "append-only" in str(exc.value).lower()
    ), f"Message inattendu du trigger : {exc.value!r}"
    db_conn.rollback()


# ---------------------------------------------------------------------------
# pipeline_runs — DELETE interdit
# ---------------------------------------------------------------------------


def test_pr_delete_forbidden(db_conn, case_factory):
    """DELETE sur pipeline_runs lève psycopg.Error 'append-only' (trigger BEFORE DELETE)."""
    if not _trigger_present(db_conn, "pipeline_runs", "trg_pipeline_runs_append_only"):
        pytest.skip("Trigger absent — test non pertinent")

    case_id = case_factory()
    run_id = _insert_pipeline_run(db_conn, case_id)

    with pytest.raises(psycopg.Error) as exc:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.pipeline_runs WHERE pipeline_run_id = %s",
                (run_id,),
            )

    assert (
        "append-only" in str(exc.value).lower()
    ), f"Message inattendu du trigger : {exc.value!r}"
    db_conn.rollback()


# ---------------------------------------------------------------------------
# pipeline_runs — INSERT valide fonctionne
# ---------------------------------------------------------------------------


def test_pr_insert_valid(db_conn, case_factory):
    """INSERT valide dans pipeline_runs fonctionne (trigger ne bloque pas INSERT)."""
    case_id = case_factory()
    run_id = _insert_pipeline_run(db_conn, case_id)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT pipeline_run_id FROM public.pipeline_runs "
            "WHERE pipeline_run_id = %s",
            (run_id,),
        )
        row = cur.fetchone()

    assert row is not None, "INSERT pipeline_runs doit réussir et la ligne doit exister"
    assert str(row["pipeline_run_id"]) == run_id


# ---------------------------------------------------------------------------
# pipeline_step_runs — trigger présent
# ---------------------------------------------------------------------------


def test_psr_trigger_present(db_conn):
    """Trigger trg_pipeline_step_runs_append_only est enregistré pour UPDATE et DELETE."""
    if not _trigger_present(
        db_conn, "pipeline_step_runs", "trg_pipeline_step_runs_append_only"
    ):
        pytest.fail(
            "trg_pipeline_step_runs_append_only absent — "
            "migration 033 non appliquée ou trigger manquant"
        )


# ---------------------------------------------------------------------------
# pipeline_step_runs — UPDATE interdit
# ---------------------------------------------------------------------------


def test_psr_update_forbidden(db_conn, case_factory):
    """UPDATE sur pipeline_step_runs lève psycopg.Error 'append-only' (BEFORE UPDATE)."""
    if not _trigger_present(
        db_conn, "pipeline_step_runs", "trg_pipeline_step_runs_append_only"
    ):
        pytest.skip("Trigger absent — test non pertinent")

    case_id = case_factory()
    run_id = _insert_pipeline_run(db_conn, case_id)
    step_id = _insert_pipeline_step_run(db_conn, run_id)

    with pytest.raises(psycopg.Error) as exc:
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE public.pipeline_step_runs SET status = 'ok' "
                "WHERE step_run_id = %s",
                (step_id,),
            )

    assert (
        "append-only" in str(exc.value).lower()
    ), f"Message inattendu du trigger : {exc.value!r}"
    db_conn.rollback()


# ---------------------------------------------------------------------------
# pipeline_step_runs — DELETE interdit
# ---------------------------------------------------------------------------


def test_psr_delete_forbidden(db_conn, case_factory):
    """DELETE sur pipeline_step_runs lève psycopg.Error 'append-only' (BEFORE DELETE)."""
    if not _trigger_present(
        db_conn, "pipeline_step_runs", "trg_pipeline_step_runs_append_only"
    ):
        pytest.skip("Trigger absent — test non pertinent")

    case_id = case_factory()
    run_id = _insert_pipeline_run(db_conn, case_id)
    step_id = _insert_pipeline_step_run(db_conn, run_id)

    with pytest.raises(psycopg.Error) as exc:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.pipeline_step_runs WHERE step_run_id = %s",
                (step_id,),
            )

    assert (
        "append-only" in str(exc.value).lower()
    ), f"Message inattendu du trigger : {exc.value!r}"
    db_conn.rollback()


# ---------------------------------------------------------------------------
# pipeline_step_runs — INSERT valide fonctionne
# ---------------------------------------------------------------------------


def test_psr_insert_valid(db_conn, case_factory):
    """INSERT valide dans pipeline_step_runs fonctionne (trigger ne bloque pas INSERT)."""
    case_id = case_factory()
    run_id = _insert_pipeline_run(db_conn, case_id)
    step_id = _insert_pipeline_step_run(db_conn, run_id)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT step_run_id FROM public.pipeline_step_runs "
            "WHERE step_run_id = %s",
            (step_id,),
        )
        row = cur.fetchone()

    assert (
        row is not None
    ), "INSERT pipeline_step_runs doit réussir et la ligne doit exister"
    assert str(row["step_run_id"]) == step_id
