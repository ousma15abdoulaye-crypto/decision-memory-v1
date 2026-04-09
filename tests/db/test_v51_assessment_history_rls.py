"""RLS ``assessment_history`` (093) — isolation tenant + deux GUC ``app.tenant_id`` / ``app.current_tenant``.

Exige DB migrée ≥ 093. Rollback via fixture ``db_transaction``.

Les PK / FK utilisent des **UUID explicites** (``gen_random_uuid()`` côté table ou
valeurs fournies en test) : aucune assertion ne repose sur des identifiants séquentiels ;
un rollback n’invalide pas ce scénario même si des séquences ailleurs en base avancent.
"""

from __future__ import annotations

import uuid

import psycopg.errors
import pytest

_RLS_SUBJECT_ROLE = "dms_rls_nobypass"


def _ensure_rls_subject_role(cur) -> None:
    """Crée le rôle sujet RLS si possible ; sinon skip (CI / DB sans CREATEROLE)."""
    try:
        cur.execute("""
            DO $body$
            BEGIN
                CREATE ROLE dms_rls_nobypass NOLOGIN NOSUPERUSER NOBYPASSRLS INHERIT;
            EXCEPTION WHEN duplicate_object THEN
                NULL;
            END
            $body$;
            """)
        cur.execute("GRANT USAGE ON SCHEMA public TO dms_rls_nobypass")
    except psycopg.errors.InsufficientPrivilege:
        cur.connection.rollback()
        pytest.skip(
            "RLS role setup: privilèges insuffisants (CREATE ROLE / GRANT USAGE schema)"
        )
    try:
        cur.execute("GRANT SELECT ON assessment_history TO dms_rls_nobypass")
    except Exception:
        cur.connection.rollback()
        pytest.skip("GRANT SELECT assessment_history impossible (droits DB)")


def _set_rls_subject_role(cur) -> None:
    _ensure_rls_subject_role(cur)
    cur.execute(f"SET ROLE {_RLS_SUBJECT_ROLE}")


def _reset_session_role(cur) -> None:
    cur.execute("RESET ROLE")


def _table_exists(cur, name: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        ) AS t
        """,
        (name,),
    )
    row = cur.fetchone()
    return bool(row and row.get("t"))


@pytest.mark.db
def test_assessment_history_rls_tenant_id_and_current_tenant_guc(
    db_transaction,
) -> None:
    cur = db_transaction
    if not _table_exists(cur, "assessment_history"):
        pytest.skip("Table assessment_history absente (migration 093 non appliquée)")

    # Avant tout INSERT : si CREATE ROLE échoue, rollback — sinon transaction avortée.
    _ensure_rls_subject_role(cur)

    tenant_id = str(uuid.uuid4())
    ws_id = str(uuid.uuid4())
    cur.execute("SELECT set_config('app.is_admin', 'true', true)")
    cur.execute(
        "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s)",
        (tenant_id, f"ah-rls-{tenant_id[:8]}", "AH RLS test"),
    )

    cur.execute("SELECT id FROM users LIMIT 1")
    urow = cur.fetchone()
    if not urow:
        pytest.skip("Aucun utilisateur en base")
    user_id = int(urow["id"])

    cur.execute(
        """
        INSERT INTO process_workspaces
            (id, tenant_id, created_by, reference_code, title, process_type, status)
        VALUES (%s, %s, %s, %s, %s, 'devis_simple', 'draft')
        """,
        (ws_id, tenant_id, user_id, f"AH-{ws_id[:8]}", "assessment_history RLS WS"),
    )

    cur.execute(
        """
        INSERT INTO supplier_bundles
            (workspace_id, tenant_id, vendor_name_raw, bundle_index)
        VALUES (%s, %s, %s, 1)
        RETURNING id
        """,
        (ws_id, tenant_id, "vendor-ah-rls"),
    )
    bundle_row = cur.fetchone()
    bundle_id = str(bundle_row["id"])

    cur.execute(
        """
        INSERT INTO criterion_assessments
            (workspace_id, tenant_id, bundle_id, criterion_key, confidence)
        VALUES (%s, %s, %s, %s, 0.8)
        RETURNING id
        """,
        (ws_id, tenant_id, bundle_id, "criterion_ah_rls"),
    )
    ca_row = cur.fetchone()
    ca_id = str(ca_row["id"])

    ah_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO assessment_history
            (id, criterion_assessment_id, workspace_id, tenant_id,
             changed_by, change_reason, change_metadata)
        VALUES (%s, %s, %s, %s, %s, %s, '{}'::jsonb)
        """,
        (
            ah_id,
            ca_id,
            ws_id,
            tenant_id,
            user_id,
            "test_rls",
        ),
    )

    other_tenant = str(uuid.uuid4())
    # Chaîne vide pour app.tenant_id / app.current_tenant → cast ::uuid invalide dans la
    # policy 093 (current_setting(..., true)::uuid). Utiliser des UUID arbitraires ≠ tenant
    # pour simuler des GUC non alignés sans casser la transaction.
    wrong_current = str(uuid.uuid4())

    try:
        _set_rls_subject_role(cur)
        cur.execute("SELECT set_config('app.is_admin', '', true)")
        cur.execute("SELECT set_config('app.tenant_id', %s, true)", (other_tenant,))
        cur.execute(
            "SELECT set_config('app.current_tenant', %s, true)", (wrong_current,)
        )
        cur.execute(
            "SELECT COUNT(*) AS c FROM assessment_history WHERE id = %s",
            (ah_id,),
        )
        assert cur.fetchone()["c"] == 0, "Autre tenant ne doit pas voir la ligne"

        cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
        cur.execute(
            "SELECT COUNT(*) AS c FROM assessment_history WHERE id = %s",
            (ah_id,),
        )
        assert cur.fetchone()["c"] == 1, "app.tenant_id aligné → visible"

        wrong_tenant_guc = str(uuid.uuid4())
        cur.execute("SELECT set_config('app.tenant_id', %s, true)", (wrong_tenant_guc,))
        cur.execute("SELECT set_config('app.current_tenant', %s, true)", (tenant_id,))
        cur.execute(
            "SELECT COUNT(*) AS c FROM assessment_history WHERE id = %s",
            (ah_id,),
        )
        assert cur.fetchone()["c"] == 1, "app.current_tenant seul → visible (2e GUC)"

        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            "SELECT COUNT(*) AS c FROM assessment_history WHERE id = %s",
            (ah_id,),
        )
        assert cur.fetchone()["c"] == 1, "admin bypass"
    finally:
        _reset_session_role(cur)
