"""
RLS — rôle dm_app (non superuser, NOBYPASSRLS).

Nécessite DATABASE_URL_RLS_TEST (ex. postgresql://dm_app:...@host/db) après :
  ALTER ROLE dm_app WITH LOGIN PASSWORD '...';

CI pose le mot de passe après alembic upgrade (voir ci-main.yml).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import psycopg
import pytest
from psycopg.rows import dict_row

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL_RLS_TEST"),
    reason="DATABASE_URL_RLS_TEST non défini — tests RLS dm_app ignorés",
)


def _rls_conn():
    url = os.environ["DATABASE_URL_RLS_TEST"].replace(
        "postgresql+psycopg://", "postgresql://"
    )
    return psycopg.connect(url, row_factory=dict_row, autocommit=False)


def _insert_case(cur, case_id: str, tenant_id: str, now: str) -> None:
    cur.execute(
        """
        INSERT INTO public.cases
            (id, case_type, title, created_at, currency, status, tenant_id)
        VALUES (%s, 'test', %s, %s, 'XOF', 'draft', %s)
        """,
        (case_id, f"rls-{tenant_id[:8]}", now, tenant_id),
    )


def test_dm_app_cannot_select_other_tenant_case(db_conn):
    """Sous app.tenant_id=A, SELECT par id d'un case du tenant B → 0 ligne."""
    tid_a = f"rls-test-a-{uuid.uuid4().hex[:8]}"
    tid_b = f"rls-test-b-{uuid.uuid4().hex[:8]}"
    case_a = str(uuid.uuid4())
    case_b = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.cases
                (id, case_type, title, created_at, currency, status, tenant_id)
            VALUES
                (%s, 'test', 'rls-a', %s, 'XOF', 'draft', %s),
                (%s, 'test', 'rls-b', %s, 'XOF', 'draft', %s)
            """,
            (case_a, now, tid_a, case_b, now, tid_b),
        )

    try:
        with _rls_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.tenant_id', %s, true)",
                    (tid_a,),
                )
                cur.execute(
                    "SELECT id FROM public.cases WHERE id = %s",
                    (case_b,),
                )
                rows = cur.fetchall()
            conn.commit()
        assert rows == [], "RLS devrait masquer le case d'un autre tenant"
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.cases WHERE id = ANY(%s)", ([case_a, case_b],)
            )


def test_dm_app_cannot_select_other_tenant_document(db_conn):
    """RLS sur documents : tenant A ne peut pas voir les documents du tenant B."""
    tid_a = f"rls-doc-a-{uuid.uuid4().hex[:8]}"
    tid_b = f"rls-doc-b-{uuid.uuid4().hex[:8]}"
    case_a = str(uuid.uuid4())
    case_b = str(uuid.uuid4())
    doc_a = str(uuid.uuid4())
    doc_b = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    with db_conn.cursor() as cur:
        _insert_case(cur, case_a, tid_a, now)
        _insert_case(cur, case_b, tid_b, now)
        cur.execute(
            """
            INSERT INTO public.documents
                (id, case_id, filename, path, uploaded_at, tenant_id)
            VALUES
                (%s, %s, 'doc-a.pdf', '/a', %s, %s),
                (%s, %s, 'doc-b.pdf', '/b', %s, %s)
            """,
            (doc_a, case_a, now, tid_a, doc_b, case_b, now, tid_b),
        )

    try:
        with _rls_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tid_a,))
                cur.execute("SELECT id FROM public.documents WHERE id = %s", (doc_b,))
                rows = cur.fetchall()
            conn.commit()
        assert rows == [], "RLS documents — tenant A ne doit pas voir doc du tenant B"
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.documents WHERE id = ANY(%s)", ([doc_a, doc_b],)
            )
            cur.execute(
                "DELETE FROM public.cases WHERE id = ANY(%s)", ([case_a, case_b],)
            )


def test_dm_app_admin_bypass_sees_all_documents(db_conn):
    """Avec is_admin=true, dm_app voit tous les documents (admin bypass)."""
    tid_a = f"rls-adm-a-{uuid.uuid4().hex[:8]}"
    tid_b = f"rls-adm-b-{uuid.uuid4().hex[:8]}"
    case_a = str(uuid.uuid4())
    case_b = str(uuid.uuid4())
    doc_a = str(uuid.uuid4())
    doc_b = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    with db_conn.cursor() as cur:
        _insert_case(cur, case_a, tid_a, now)
        _insert_case(cur, case_b, tid_b, now)
        cur.execute(
            """
            INSERT INTO public.documents
                (id, case_id, filename, path, uploaded_at, tenant_id)
            VALUES
                (%s, %s, 'doc-a.pdf', '/a', %s, %s),
                (%s, %s, 'doc-b.pdf', '/b', %s, %s)
            """,
            (doc_a, case_a, now, tid_a, doc_b, case_b, now, tid_b),
        )

    try:
        with _rls_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tid_a,))
                cur.execute("SELECT set_config('app.is_admin', 'true', true)")
                cur.execute(
                    "SELECT id FROM public.documents WHERE id = ANY(%s)",
                    ([doc_a, doc_b],),
                )
                rows = cur.fetchall()
            conn.commit()
        ids = {r["id"] for r in rows}
        assert (
            doc_a in ids and doc_b in ids
        ), "Admin doit voir tous les documents quelle que soit le tenant"
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.documents WHERE id = ANY(%s)", ([doc_a, doc_b],)
            )
            cur.execute(
                "DELETE FROM public.cases WHERE id = ANY(%s)", ([case_a, case_b],)
            )


def test_dm_app_cannot_select_other_tenant_extraction_job(db_conn):
    """RLS sur extraction_jobs : tenant A ne voit pas les jobs du tenant B."""
    tid_a = f"rls-ej-a-{uuid.uuid4().hex[:8]}"
    tid_b = f"rls-ej-b-{uuid.uuid4().hex[:8]}"
    case_a = str(uuid.uuid4())
    case_b = str(uuid.uuid4())
    doc_a = str(uuid.uuid4())
    doc_b = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    with db_conn.cursor() as cur:
        _insert_case(cur, case_a, tid_a, now)
        _insert_case(cur, case_b, tid_b, now)
        cur.execute(
            """
            INSERT INTO public.documents
                (id, case_id, filename, path, uploaded_at, tenant_id)
            VALUES
                (%s, %s, 'doc-a.pdf', '/a', %s, %s),
                (%s, %s, 'doc-b.pdf', '/b', %s, %s)
            """,
            (doc_a, case_a, now, tid_a, doc_b, case_b, now, tid_b),
        )
        cur.execute(
            """
            INSERT INTO public.extraction_jobs
                (document_id, status, method, sla_class)
            VALUES
                (%s, 'pending', 'native_pdf', 'A'),
                (%s, 'pending', 'native_pdf', 'A')
            RETURNING id
            """,
            (doc_a, doc_b),
        )
        job_rows = cur.fetchall()
        job_a_id = job_rows[0]["id"]
        job_b_id = job_rows[1]["id"]

    try:
        with _rls_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tid_a,))
                cur.execute(
                    "SELECT id FROM public.extraction_jobs WHERE id = %s",
                    (str(job_b_id),),
                )
                rows = cur.fetchall()
            conn.commit()
        assert (
            rows == []
        ), "RLS extraction_jobs — tenant A ne doit pas voir le job du tenant B"
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.extraction_jobs WHERE id = ANY(%s)",
                ([str(job_a_id), str(job_b_id)],),
            )
            cur.execute(
                "DELETE FROM public.documents WHERE id = ANY(%s)", ([doc_a, doc_b],)
            )
            cur.execute(
                "DELETE FROM public.cases WHERE id = ANY(%s)", ([case_a, case_b],)
            )
