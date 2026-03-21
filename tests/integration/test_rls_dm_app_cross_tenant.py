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
