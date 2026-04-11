"""097 — Assign supply_chain role to test user ID 100 (V5.2 agent.query access).

Revision ID: 097_fix_test_user_role_supply_chain
Revises: 096_dms_embeddings_tenant_rls

Context
-------
User ID 100 (ousma15abdoulaye@gmail.com) carries role_id=2 which maps to the
legacy V4.x role ``procurement_officer``.  This role is absent from the V5.2
ROLE_PERMISSIONS matrix in ``src/auth/permissions.py``, so the agent endpoint
raises 403 Forbidden when checking ``agent.query``.

Changes
-------
1. Ensure a ``supply_chain`` entry exists in the legacy ``roles`` table so that
   ``users.role_id`` can reference it.  The legacy table is the source of truth
   for ``role_name`` returned by ``get_user_by_id`` / ``authenticate_user``.

2. Update ``users.role_id`` for user ID 100 to the ``supply_chain`` role.

3. Upsert ``user_tenant_roles`` for user 100 to the ``supply_chain`` rbac role
   (V5.2 RBAC table seeded by migration 075).  The ``supply_chain`` rbac role
   does not exist in 075 (which uses ``supply_chain_admin``); it is the V5.2
   role defined in ``src/auth/permissions.py``.  We insert it into
   ``rbac_roles`` if absent, then assign it to user 100.

Downgrade
---------
Restores user 100 to ``procurement_officer`` (role_id=2) and removes the
``supply_chain`` user_tenant_roles row.  The ``supply_chain`` rbac_roles row
is left in place (safe — no other rows depend on it after downgrade).

REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "097_fix_test_user_role_supply_chain"
down_revision = "096_dms_embeddings_tenant_rls"
branch_labels = None
depends_on = None

_TARGET_USER_ID = 100
_ROLE_NAME = "supply_chain"
_LEGACY_ROLE_DESCRIPTION = "Supply chain officer — V5.2 agent.query access"


def upgrade() -> None:
    # ── 1. Ensure supply_chain exists in legacy roles table ──────────────────
    # The legacy ``roles`` table (migration 004) is the FK target for
    # ``users.role_id``.  ``authenticate_user`` JOINs it to get ``role_name``,
    # which is then mapped to a JWT role via ``_ROLE_MAPPING`` in auth_router.py.
    op.execute(f"""
        INSERT INTO roles (name, description, created_at)
        VALUES (
            '{_ROLE_NAME}',
            '{_LEGACY_ROLE_DESCRIPTION}',
            NOW()::text
        )
        ON CONFLICT (name) DO NOTHING
    """)

    # ── 2. Update user 100's role_id to supply_chain ─────────────────────────
    op.execute(f"""
        UPDATE users
        SET role_id = (
            SELECT id FROM roles WHERE name = '{_ROLE_NAME}' LIMIT 1
        )
        WHERE id = {_TARGET_USER_ID}
    """)

    # ── 3. Ensure supply_chain exists in rbac_roles (V5.2 RBAC) ─────────────
    # Migration 075 seeded V4.2.0 roles (procurement_director, supply_chain_admin,
    # etc.) but not the V5.2 ``supply_chain`` role used by src/auth/permissions.py.
    # Insert it as a non-system role so it can be assigned without affecting the
    # V4.2.0 role matrix.
    op.execute(f"""
        INSERT INTO rbac_roles (code, description, is_system)
        VALUES (
            '{_ROLE_NAME}',
            'Supply chain officer V5.2 — 15 permissions including agent.query',
            FALSE
        )
        ON CONFLICT (code) DO NOTHING
    """)

    # ── 4. Upsert user_tenant_roles for user 100 → supply_chain ─────────────
    # Remove any existing procurement_officer assignment for this user so the
    # JWT role resolution is unambiguous, then insert supply_chain.
    op.execute(f"""
        DELETE FROM user_tenant_roles
        WHERE user_id = {_TARGET_USER_ID}
          AND role_id IN (
              SELECT id FROM rbac_roles WHERE code = 'procurement_officer'
          )
    """)

    op.execute(f"""
        INSERT INTO user_tenant_roles (user_id, tenant_id, role_id)
        SELECT
            {_TARGET_USER_ID},
            ut.tenant_id::uuid,
            r.id
        FROM user_tenants ut
        CROSS JOIN rbac_roles r
        WHERE ut.user_id = {_TARGET_USER_ID}
          AND r.code = '{_ROLE_NAME}'
        ON CONFLICT (user_id, tenant_id, role_id) DO NOTHING
    """)

    # ── 5. Verification (FAIL-LOUD) ──────────────────────────────────────────
    op.execute(f"""
        DO $$
        DECLARE
            v_role_name TEXT;
            v_rbac_count INTEGER;
        BEGIN
            SELECT r.name INTO v_role_name
            FROM users u
            JOIN roles r ON r.id = u.role_id
            WHERE u.id = {_TARGET_USER_ID};

            IF v_role_name IS NULL THEN
                RAISE EXCEPTION
                    '097 UPGRADE FAILED — user {_TARGET_USER_ID} not found';
            END IF;

            IF v_role_name != '{_ROLE_NAME}' THEN
                RAISE EXCEPTION
                    '097 UPGRADE FAILED — user {_TARGET_USER_ID} role is % (expected {_ROLE_NAME})',
                    v_role_name;
            END IF;

            SELECT COUNT(*) INTO v_rbac_count
            FROM user_tenant_roles utr
            JOIN rbac_roles r ON r.id = utr.role_id
            WHERE utr.user_id = {_TARGET_USER_ID}
              AND r.code = '{_ROLE_NAME}';

            IF v_rbac_count = 0 THEN
                RAISE WARNING
                    '097 — user {_TARGET_USER_ID} has no user_tenants row; '
                    'user_tenant_roles not assigned (tenant provisioning required)';
            END IF;

            RAISE NOTICE
                '097 OK — user {_TARGET_USER_ID} role=% rbac_rows=%',
                v_role_name, v_rbac_count;
        END;
        $$
    """)


def downgrade() -> None:
    # Restore user 100 to procurement_officer (role_id=2 per migration 004 seed)
    op.execute(f"""
        UPDATE users
        SET role_id = (
            SELECT id FROM roles WHERE name = 'procurement_officer' LIMIT 1
        )
        WHERE id = {_TARGET_USER_ID}
    """)

    # Remove the supply_chain user_tenant_roles assignment
    op.execute(f"""
        DELETE FROM user_tenant_roles
        WHERE user_id = {_TARGET_USER_ID}
          AND role_id IN (
              SELECT id FROM rbac_roles WHERE code = '{_ROLE_NAME}'
          )
    """)

    # Re-insert procurement_officer user_tenant_roles
    op.execute(f"""
        INSERT INTO user_tenant_roles (user_id, tenant_id, role_id)
        SELECT
            {_TARGET_USER_ID},
            ut.tenant_id::uuid,
            r.id
        FROM user_tenants ut
        CROSS JOIN rbac_roles r
        WHERE ut.user_id = {_TARGET_USER_ID}
          AND r.code = 'procurement_officer'
        ON CONFLICT (user_id, tenant_id, role_id) DO NOTHING
    """)
