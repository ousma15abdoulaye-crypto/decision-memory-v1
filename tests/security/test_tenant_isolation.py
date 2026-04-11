"""Tests isolation tenant — tables marché / mercuriale (post-migration 094).

Exige DB live + migrations à jour (``094_security_market_mercurial_tenant_rls``).
Politique : ``tenant_id = current_setting('app.current_tenant')::uuid``.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

TENANT_A = str(uuid.uuid4())
TENANT_B = str(uuid.uuid4())

_RLS_SUBJECT_ROLE = "dms_rls_nobypass_sec"


def _ensure_role(cur) -> None:
    cur.execute("""
        DO $body$
        BEGIN
            CREATE ROLE dms_rls_nobypass_sec NOLOGIN NOSUPERUSER NOBYPASSRLS INHERIT;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END
        $body$;
    """)
    cur.execute("GRANT USAGE ON SCHEMA public TO dms_rls_nobypass_sec")
    for tbl in (
        "market_surveys",
        "mercurials",
        "market_signals_v2",
        "mercuriale_sources",
    ):
        cur.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON public.{tbl} TO dms_rls_nobypass_sec"
        )


def _set_subject(cur) -> None:
    _ensure_role(cur)
    cur.execute(f"SET ROLE {_RLS_SUBJECT_ROLE}")


def _reset_role(cur) -> None:
    cur.execute("RESET ROLE")


def _set_tenant(cur, tid: str) -> None:
    cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tid,))
    cur.execute("SELECT set_config('app.current_tenant', %s, true)", (tid,))
    cur.execute("SELECT set_config('app.is_admin', '', true)")


@pytest.mark.db
def test_market_surveys_rls_two_tenants(db_transaction):
    """Tenant B ne voit pas les enquêtes du tenant A."""
    cur = db_transaction
    cur.execute("SELECT set_config('app.is_admin', 'true', true)")
    cur.execute(
        "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (TENANT_A, f"sec-a-{TENANT_A[:8]}", "Sec A"),
    )
    cur.execute(
        "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (TENANT_B, f"sec-b-{TENANT_B[:8]}", "Sec B"),
    )
    cur.execute("SELECT id FROM users LIMIT 1")
    row = cur.fetchone()
    if not row:
        pytest.skip("No users in DB")
    uid = row["id"]

    cur.execute("SELECT item_id FROM couche_b.procurement_dict_items LIMIT 1")
    ir = cur.fetchone()
    if not ir:
        pytest.skip("No procurement_dict_items — cannot insert market_surveys")
    item_id = ir["item_id"]

    cur.execute("SELECT id FROM geo_master LIMIT 1")
    gr = cur.fetchone()
    if not gr:
        pytest.skip("No geo_master — cannot insert market_surveys")
    zone_id = gr["id"]

    ws_a = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO process_workspaces
            (id, tenant_id, created_by, reference_code, title, process_type, status)
        VALUES (%s, %s, %s, %s, %s, 'devis_simple', 'draft')
        """,
        (ws_a, TENANT_A, uid, f"SEC-{ws_a[:8]}", "Sec workspace"),
    )

    sid = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO market_surveys (
            id, item_id, price_quoted, currency, quantity_surveyed,
            supplier_raw, zone_id, date_surveyed, tenant_id, workspace_id
        ) VALUES (
            %s, %s, 1000, 'XOF', 1.0,
            'Test Supplier', %s,
            CURRENT_DATE, %s, %s
        )
        """,
        (sid, item_id, zone_id, TENANT_A, ws_a),
    )

    try:
        _set_subject(cur)
        _set_tenant(cur, TENANT_A)
        cur.execute("SELECT COUNT(*) AS c FROM market_surveys WHERE id = %s", (sid,))
        assert cur.fetchone()["c"] == 1

        _set_tenant(cur, TENANT_B)
        cur.execute("SELECT COUNT(*) AS c FROM market_surveys WHERE id = %s", (sid,))
        assert cur.fetchone()["c"] == 0
    finally:
        _reset_role(cur)
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute("DELETE FROM market_surveys WHERE id = %s", (sid,))
        cur.execute("DELETE FROM process_workspaces WHERE id = %s", (ws_a,))


@pytest.mark.db
def test_mercurials_rls_insert_other_tenant_denied(db_transaction):
    """INSERT avec mauvais tenant_id doit échouer sous RLS (WITH CHECK)."""
    cur = db_transaction
    cur.execute("SELECT set_config('app.is_admin', 'true', true)")
    cur.execute(
        "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (TENANT_A, f"sec2-a-{TENANT_A[:8]}", "Sec2 A"),
    )
    cur.execute(
        "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (TENANT_B, f"sec2-b-{TENANT_B[:8]}", "Sec2 B"),
    )

    src_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO mercuriale_sources (
            id, filename, sha256, year, source_type, parse_status, extraction_engine, tenant_id
        ) VALUES (
            %s, 'sec-test.csv', %s, 2024, 'custom', 'done', 'test', %s
        )
        """,
        (src_id, f"sha256-{src_id[:20]}", TENANT_A),
    )

    cur.execute("SELECT id FROM geo_master LIMIT 1")
    gz = cur.fetchone()
    if not gz:
        pytest.skip("No geo_master")
    zid = gz["id"]

    try:
        _set_subject(cur)
        _set_tenant(cur, TENANT_B)
        cur.execute("SAVEPOINT sec_merc_rls_try")
        try:
            cur.execute(
                """
                INSERT INTO mercurials (
                    source_id, item_canonical, price_min, price_avg, price_max,
                    unit_price, year, zone_id, tenant_id
                ) VALUES (%s, 'test_item', 1, 2, 3, 2, 2024, %s, %s)
                """,
                (src_id, zid, TENANT_A),
            )
        except psycopg.Error as e:
            cur.execute("ROLLBACK TO SAVEPOINT sec_merc_rls_try")
            msg = str(e).lower()
            assert (
                "row-level security" in msg
                or "violates" in msg
                or (e.diag is not None and e.diag.sqlstate == "42501")
            ), e
        else:
            cur.execute("ROLLBACK TO SAVEPOINT sec_merc_rls_try")
            pytest.fail(
                "INSERT cross-tenant aurait dû être refusé par RLS (WITH CHECK)"
            )
    finally:
        _reset_role(cur)
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute("DELETE FROM mercurials WHERE source_id = %s", (src_id,))
        cur.execute("DELETE FROM mercuriale_sources WHERE id = %s", (src_id,))
