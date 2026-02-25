"""
T-L12 : DB-level append-only — analysis_summaries.
4 tests — corps complets — INV-AS3 / INV-AS9b.
"""

from __future__ import annotations

import json
import uuid

import psycopg
import pytest


@pytest.fixture
def analysis_summary_row(db_conn, case_factory):
    """
    Insère une ligne minimale dans analysis_summaries.
    Pas de rollback explicite dans la fixture.
    Aucun DELETE de teardown : analysis_summaries est append-only by design.
    """
    case_id = case_factory("XOF")
    summary_id = str(uuid.uuid4())
    result_hash = f"test_hash_{uuid.uuid4().hex}"

    minimal_summary = {
        "summary_id": summary_id,
        "case_id": case_id,
        "pipeline_run_id": None,
        "summary_version": "v1",
        "summary_status": "blocked",
        "triggered_by": "test_append_only",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "sections": [],
        "warnings": [],
        "errors": [],
        "result_hash": result_hash,
    }

    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.analysis_summaries (
                summary_id, case_id, pipeline_run_id,
                summary_version, summary_status,
                result_jsonb, error_jsonb,
                result_hash, triggered_by,
                generated_at, created_at
            ) VALUES (
                %s, %s, NULL,
                'v1', 'blocked',
                %s::jsonb, '[]'::jsonb,
                %s, 'test_append_only',
                NOW(), NOW()
            )
            """,
            (summary_id, case_id, json.dumps(minimal_summary), result_hash),
        )
        # Pré-condition
        cur.execute(
            "SELECT COUNT(*) AS n FROM public.analysis_summaries "
            "WHERE summary_id = %s",
            (summary_id,),
        )
        row = cur.fetchone()
        count = row["n"] if isinstance(row, dict) else row[0]
        assert count == 1, f"Pré-condition : ligne non insérée ({summary_id})"

    yield summary_id, result_hash
    # Zéro DELETE de cleanup — analysis_summaries est append-only by design.
    # Pattern identique aux tests pipeline_runs (ADR-0012).


def test_analysis_summaries_update_forbidden(db_conn, analysis_summary_row):
    """
    UPDATE analysis_summaries → trigger RAISE EXCEPTION contenant 'append-only'.
    INV-AS3.
    """
    summary_id, _ = analysis_summary_row
    with pytest.raises(psycopg.Error) as exc_info:
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE public.analysis_summaries "
                "SET summary_status = 'ready' "
                "WHERE summary_id = %s",
                (summary_id,),
            )
    assert (
        "append-only" in str(exc_info.value).lower()
    ), f"Message trigger inattendu : {exc_info.value}"
    db_conn.rollback()


def test_analysis_summaries_delete_forbidden(db_conn, analysis_summary_row):
    """
    DELETE analysis_summaries → trigger RAISE EXCEPTION contenant 'append-only'.
    INV-AS3.
    """
    summary_id, _ = analysis_summary_row
    with pytest.raises(psycopg.Error) as exc_info:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.analysis_summaries " "WHERE summary_id = %s",
                (summary_id,),
            )
    assert (
        "append-only" in str(exc_info.value).lower()
    ), f"Message trigger inattendu : {exc_info.value}"
    db_conn.rollback()


def test_analysis_summaries_insert_allowed(db_conn, case_factory):
    """
    INSERT analysis_summaries → autorisé (append-only = lecture + écriture, pas update/delete).
    INV-AS3 — preuve que le trigger ne bloque pas les INSERTs.
    """
    case_id = case_factory("XOF")
    summary_id = str(uuid.uuid4())
    result_hash = f"test_insert_{uuid.uuid4().hex}"

    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.analysis_summaries (
                summary_id, case_id, pipeline_run_id,
                summary_version, summary_status,
                result_jsonb, error_jsonb,
                result_hash, triggered_by,
                generated_at, created_at
            ) VALUES (
                %s, %s, NULL, 'v1', 'blocked',
                '{}'::jsonb, '[]'::jsonb,
                %s, 'test_insert', NOW(), NOW()
            )
            """,
            (summary_id, case_id, result_hash),
        )
        cur.execute(
            "SELECT COUNT(*) AS n FROM public.analysis_summaries "
            "WHERE summary_id = %s",
            (summary_id,),
        )
        row = cur.fetchone()
        count = row["n"] if isinstance(row, dict) else row[0]

    assert count == 1, "INSERT refusé — INV-AS3 trop restrictif"


def test_analysis_summaries_unique_result_hash_enforced(db_conn, case_factory):
    """
    UNIQUE(result_hash) — deux lignes avec le même hash → exception DB.
    INV-AS9b.
    """
    case_id = case_factory("XOF")
    shared_hash = f"shared_hash_{uuid.uuid4().hex}"

    with db_conn.cursor() as cur:
        # Première insertion — OK
        cur.execute(
            """
            INSERT INTO public.analysis_summaries (
                summary_id, case_id, pipeline_run_id,
                summary_version, summary_status,
                result_jsonb, error_jsonb,
                result_hash, triggered_by,
                generated_at, created_at
            ) VALUES (
                %s, %s, NULL, 'v1', 'blocked',
                '{}'::jsonb, '[]'::jsonb,
                %s, 'test_unique_1', NOW(), NOW()
            )
            """,
            (str(uuid.uuid4()), case_id, shared_hash),
        )

    # Deuxième insertion avec même hash → doit échouer
    with pytest.raises(psycopg.Error) as exc_info:
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.analysis_summaries (
                    summary_id, case_id, pipeline_run_id,
                    summary_version, summary_status,
                    result_jsonb, error_jsonb,
                    result_hash, triggered_by,
                    generated_at, created_at
                ) VALUES (
                    %s, %s, NULL, 'v1', 'blocked',
                    '{}'::jsonb, '[]'::jsonb,
                    %s, 'test_unique_2', NOW(), NOW()
                )
                """,
                (str(uuid.uuid4()), case_id, shared_hash),
            )

    error_msg = str(exc_info.value).lower()
    assert (
        "unique" in error_msg or "duplicate" in error_msg
    ), f"Erreur UNIQUE inattendue : {exc_info.value}"
    db_conn.rollback()
