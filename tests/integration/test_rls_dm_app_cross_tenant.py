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


def _insert_test_user(cur) -> int:
    """Crée un utilisateur minimal ; user_tenants.user_id est INTEGER → FK users(id)."""
    cur.execute(
        """
        INSERT INTO public.users
            (email, username, hashed_password, full_name, is_active, is_superuser, role_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            f"rls_ut_{uuid.uuid4().hex[:10]}@test.local",
            f"rls_ut_{uuid.uuid4().hex[:10]}",
            "$2b$12$dummyhashfortestsxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "RLS test user",
            True,
            False,
            1,
            datetime.now(UTC).isoformat(),
        ),
    )
    row = cur.fetchone()
    return int(row["id"])


def _insert_user_tenant(cur, user_id: int, tenant_id: str) -> None:
    cur.execute(
        """
        INSERT INTO public.user_tenants (user_id, tenant_id)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO NOTHING
        """,
        (user_id, tenant_id),
    )


def test_dm_app_user_tenants_self_isolation(db_conn):
    """Sous app.user_id=U1, SELECT user_tenants ne retourne que les lignes de U1."""
    tid = f"rls-ut-{uuid.uuid4().hex[:8]}"

    with db_conn.cursor() as cur:
        uid_a = _insert_test_user(cur)
        uid_b = _insert_test_user(cur)
        _insert_user_tenant(cur, uid_a, tid)
        _insert_user_tenant(cur, uid_b, tid)
    db_conn.commit()

    try:
        with _rls_conn() as conn:
            with conn.cursor() as cur:
                # Policy compare user_id::text à current_setting('app.user_id')
                cur.execute(
                    "SELECT set_config('app.user_id', %s, true)",
                    (str(uid_a),),
                )
                cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tid,))
                cur.execute(
                    "SELECT user_id FROM public.user_tenants WHERE user_id = %s",
                    (uid_b,),
                )
                rows = cur.fetchall()
            conn.commit()
        assert (
            rows == []
        ), "RLS user_tenants — user A ne doit pas voir les lignes de user B"
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.users WHERE id = ANY(%s)",
                ([uid_a, uid_b],),
            )


def test_dm_app_admin_bypass_sees_all_user_tenants(db_conn):
    """Sous app.is_admin=true, SELECT user_tenants retourne toutes les lignes."""
    tid = f"rls-ut-adm-{uuid.uuid4().hex[:8]}"

    with db_conn.cursor() as cur:
        uid_a = _insert_test_user(cur)
        uid_b = _insert_test_user(cur)
        _insert_user_tenant(cur, uid_a, tid)
        _insert_user_tenant(cur, uid_b, tid)
    db_conn.commit()

    try:
        with _rls_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.is_admin', 'true', true)", ())
                cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tid,))
                cur.execute(
                    "SELECT user_id FROM public.user_tenants WHERE user_id = ANY(%s)",
                    ([uid_a, uid_b],),
                )
                rows = cur.fetchall()
            conn.commit()
        found_ids = {r["user_id"] for r in rows}
        assert (
            uid_a in found_ids and uid_b in found_ids
        ), "Admin doit voir toutes les lignes user_tenants"
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.users WHERE id = ANY(%s)",
                ([uid_a, uid_b],),
            )


# ── M13 Regulatory Profile — tenant isolation ──────────────────────


def test_dm_app_cannot_select_other_tenant_m13_profile(db_conn):
    """RLS sur m13_regulatory_profile_versions : tenant A ne voit pas tenant B."""
    tid_a = f"rls-m13p-a-{uuid.uuid4().hex[:8]}"
    tid_b = f"rls-m13p-b-{uuid.uuid4().hex[:8]}"
    case_a = str(uuid.uuid4())
    case_b = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    with db_conn.cursor() as cur:
        _insert_case(cur, case_a, tid_a, now)
        _insert_case(cur, case_b, tid_b, now)
        cur.execute(
            """
            INSERT INTO public.m13_regulatory_profile_versions
                (case_id, version, payload)
            VALUES
                (%s, 1, '{"test": "a"}'::jsonb),
                (%s, 1, '{"test": "b"}'::jsonb)
            """,
            (case_a, case_b),
        )

    try:
        with _rls_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tid_a,))
                cur.execute(
                    "SELECT id FROM public.m13_regulatory_profile_versions "
                    "WHERE case_id = %s",
                    (case_b,),
                )
                rows = cur.fetchall()
            conn.commit()
        assert (
            rows == []
        ), "RLS m13_regulatory_profile_versions — tenant A ne doit pas voir tenant B"
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.m13_regulatory_profile_versions "
                "WHERE case_id = ANY(%s)",
                ([case_a, case_b],),
            )
            cur.execute(
                "DELETE FROM public.cases WHERE id = ANY(%s)", ([case_a, case_b],)
            )


def test_dm_app_cannot_select_other_tenant_m13_correction_log(db_conn):
    """RLS sur m13_correction_log : tenant A ne voit pas tenant B."""
    tid_a = f"rls-m13c-a-{uuid.uuid4().hex[:8]}"
    tid_b = f"rls-m13c-b-{uuid.uuid4().hex[:8]}"
    case_a = str(uuid.uuid4())
    case_b = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    with db_conn.cursor() as cur:
        _insert_case(cur, case_a, tid_a, now)
        _insert_case(cur, case_b, tid_b, now)
        cur.execute(
            """
            INSERT INTO public.m13_correction_log
                (case_id, field_path, value_predicted, value_corrected)
            VALUES
                (%s, 'test.field', 'old_a', 'new_a'),
                (%s, 'test.field', 'old_b', 'new_b')
            """,
            (case_a, case_b),
        )

    try:
        with _rls_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tid_a,))
                cur.execute(
                    "SELECT id FROM public.m13_correction_log WHERE case_id = %s",
                    (case_b,),
                )
                rows = cur.fetchall()
            conn.commit()
        assert rows == [], "RLS m13_correction_log — tenant A ne doit pas voir tenant B"
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.m13_correction_log WHERE case_id = ANY(%s)",
                ([case_a, case_b],),
            )
            cur.execute(
                "DELETE FROM public.cases WHERE id = ANY(%s)", ([case_a, case_b],)
            )
