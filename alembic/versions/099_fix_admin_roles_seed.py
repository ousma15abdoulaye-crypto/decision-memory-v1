"""099 — Ensure roles seed and admin user are correctly configured for login.

Revision ID: 099_fix_admin_roles_seed
Revises: 098_primary_admin_email_owner_mandate

Problem
-------
Admin login returns 422 / 401 because ``get_user_by_login`` does an INNER JOIN
between ``users`` and ``roles``.  If the ``roles`` table is missing any of the
three required rows (admin, procurement_officer, viewer), or if the admin
user's ``role_id`` references a non-existent role ID, the JOIN returns NULL
and authentication fails silently.

Root causes that can occur on a fresh or partially-migrated database:

1. ``roles`` table exists but is empty (migration 004 ran CREATE TABLE but the
   INSERT was skipped due to a transaction rollback or partial execution).
2. ``roles`` table has rows but the IDENTITY sequence assigned IDs in a
   different order than expected (e.g. 'admin' got id=2 instead of id=1).
3. The admin user row has ``role_id=1`` hardcoded (migration 004 seed) but
   the 'admin' role was assigned a different ID by the IDENTITY sequence.
4. The admin user row is missing entirely (ON CONFLICT DO NOTHING on username
   skipped the INSERT but the email conflict was not checked).
5. ``user_tenants`` row is missing for the admin user, causing
   ``resolve_tenant_uuid_for_jwt`` to fall back to the first active tenant
   (acceptable) but also causing ``user_tenant_roles`` to be absent, which
   can trigger 403 on RBAC-protected endpoints.

Fix
---
This migration uses a single PL/pgSQL block to:

1. Ensure all three legacy roles exist (admin, procurement_officer, viewer)
   using INSERT … ON CONFLICT DO NOTHING — safe to re-run.
2. Ensure the admin user (email=ousma15abdoulaye@gmail.com, username=admin)
   exists with:
   - ``role_id`` pointing to the 'admin' role (looked up by name, not by
     hardcoded integer).
   - ``is_superuser = TRUE``, ``is_active = TRUE``.
   - The canonical bcrypt hash for password "admin123".
   If the user already exists, only ``role_id``, ``is_superuser``, and
   ``is_active`` are corrected — the password hash is NOT overwritten so that
   any password change made by the owner is preserved.
3. Ensure a ``user_tenants`` row exists for the admin user, pointing to the
   default tenant (code='sci_mali' or first active tenant).
4. Ensure a ``user_tenant_roles`` row exists for the admin user in the
   ``supply_chain_admin`` rbac role (the V4.2.0+ role that maps to 'admin'
   JWT role via ``jwt_role_for_user_row``).

REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "099_fix_admin_roles_seed"
down_revision = "098_primary_admin_email_owner_mandate"
branch_labels = None
depends_on = None

# Canonical bcrypt hash for "admin123" (cost=12).
# Generated with: python -c "import bcrypt; print(bcrypt.hashpw(b'admin123', bcrypt.gensalt(12)).decode())"
# This hash is only used when creating a brand-new admin user row; existing
# rows keep their current hashed_password unchanged.
_ADMIN_HASH = "$2b$12$n19PjDhu0vc01dy0LDWnZ.n8fX4z8tKiNGVwON4wTavaaGXOXFvDG"
_ADMIN_EMAIL = "ousma15abdoulaye@gmail.com"
_ADMIN_USERNAME = "admin"


def upgrade() -> None:
    op.execute(f"""
        DO $$
        DECLARE
            v_admin_role_id     INTEGER;
            v_viewer_role_id    INTEGER;
            v_admin_user_id     INTEGER;
            v_tenant_id_text    TEXT;
            v_rbac_role_id      UUID;
            v_now               TEXT := NOW()::text;
        BEGIN
            -- ── 1. Ensure legacy roles exist ─────────────────────────────────
            -- Use INSERT … ON CONFLICT DO NOTHING so this is idempotent.
            -- We do NOT rely on hardcoded IDs; we look up by name afterwards.
            INSERT INTO roles (name, description, created_at)
            VALUES
                ('admin',               'Full system access',                v_now),
                ('procurement_officer', 'Can create and manage own cases',   v_now),
                ('viewer',              'Read-only access',                  v_now)
            ON CONFLICT (name) DO NOTHING;

            SELECT id INTO v_admin_role_id  FROM roles WHERE name = 'admin'  LIMIT 1;
            SELECT id INTO v_viewer_role_id FROM roles WHERE name = 'viewer' LIMIT 1;

            IF v_admin_role_id IS NULL THEN
                RAISE EXCEPTION '099 FAILED — could not resolve admin role id after INSERT';
            END IF;

            RAISE NOTICE '099 — admin role id=%', v_admin_role_id;

            -- ── 2. Ensure admin user exists with correct role_id ─────────────
            -- Check by email first (canonical identity), then by username.
            SELECT id INTO v_admin_user_id
            FROM users
            WHERE lower(trim(email)) = lower('{_ADMIN_EMAIL}')
            LIMIT 1;

            IF v_admin_user_id IS NULL THEN
                SELECT id INTO v_admin_user_id
                FROM users
                WHERE username = '{_ADMIN_USERNAME}'
                LIMIT 1;
            END IF;

            IF v_admin_user_id IS NULL THEN
                -- Create the admin user from scratch.
                INSERT INTO users (
                    email, username, hashed_password, full_name,
                    is_active, is_superuser, role_id, created_at
                )
                VALUES (
                    '{_ADMIN_EMAIL}',
                    '{_ADMIN_USERNAME}',
                    '{_ADMIN_HASH}',
                    'System Administrator',
                    TRUE, TRUE,
                    v_admin_role_id,
                    v_now
                )
                RETURNING id INTO v_admin_user_id;

                RAISE NOTICE '099 — admin user created (id=%)', v_admin_user_id;
            ELSE
                -- User exists: fix role_id, is_superuser, is_active.
                -- Do NOT touch hashed_password (preserve owner password changes).
                -- Do NOT touch email/username if they already match.
                UPDATE users
                SET
                    role_id      = v_admin_role_id,
                    is_superuser = TRUE,
                    is_active    = TRUE,
                    email        = CASE
                                       WHEN lower(trim(email)) != lower('{_ADMIN_EMAIL}')
                                       THEN '{_ADMIN_EMAIL}'
                                       ELSE email
                                   END,
                    username     = CASE
                                       WHEN username != '{_ADMIN_USERNAME}'
                                       THEN '{_ADMIN_USERNAME}'
                                       ELSE username
                                   END
                WHERE id = v_admin_user_id;

                RAISE NOTICE '099 — admin user updated (id=%, role_id=%)',
                    v_admin_user_id, v_admin_role_id;
            END IF;

            -- ── 3. Ensure user_tenants row exists ────────────────────────────
            -- Resolve the default tenant UUID (sci_mali or first active tenant).
            SELECT id::text INTO v_tenant_id_text
            FROM tenants
            WHERE code = 'sci_mali' AND is_active = TRUE
            LIMIT 1;

            IF v_tenant_id_text IS NULL THEN
                SELECT id::text INTO v_tenant_id_text
                FROM tenants
                WHERE is_active = TRUE
                ORDER BY created_at
                LIMIT 1;
            END IF;

            IF v_tenant_id_text IS NULL THEN
                RAISE WARNING '099 — no active tenant found; skipping user_tenants / user_tenant_roles';
            ELSE
                INSERT INTO user_tenants (user_id, tenant_id)
                VALUES (v_admin_user_id, v_tenant_id_text)
                ON CONFLICT (user_id) DO UPDATE
                    SET tenant_id = EXCLUDED.tenant_id
                    WHERE user_tenants.tenant_id ~ '^tenant-[0-9]+$';

                RAISE NOTICE '099 — user_tenants ensured (user_id=%, tenant_id=%)',
                    v_admin_user_id, v_tenant_id_text;

                -- ── 4. Ensure user_tenant_roles row (supply_chain_admin) ─────
                -- Only if rbac_roles table exists (migration 075+).
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'rbac_roles'
                ) THEN
                    SELECT id INTO v_rbac_role_id
                    FROM rbac_roles
                    WHERE code = 'supply_chain_admin'
                    LIMIT 1;

                    IF v_rbac_role_id IS NOT NULL THEN
                        INSERT INTO user_tenant_roles (user_id, tenant_id, role_id)
                        VALUES (
                            v_admin_user_id,
                            v_tenant_id_text::uuid,
                            v_rbac_role_id
                        )
                        ON CONFLICT (user_id, tenant_id, role_id) DO NOTHING;

                        RAISE NOTICE '099 — user_tenant_roles ensured (supply_chain_admin)';
                    ELSE
                        RAISE WARNING '099 — rbac_roles has no supply_chain_admin row; skipping user_tenant_roles';
                    END IF;
                END IF;
            END IF;

            -- ── 5. Verification (FAIL-LOUD) ──────────────────────────────────
            DECLARE
                v_check_role TEXT;
                v_check_super BOOLEAN;
            BEGIN
                SELECT r.name, u.is_superuser
                INTO v_check_role, v_check_super
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = v_admin_user_id;

                IF v_check_role IS NULL THEN
                    RAISE EXCEPTION
                        '099 VERIFICATION FAILED — admin user (id=%) has no matching role in roles table '
                        '(role_id FK broken). Login will return 401.',
                        v_admin_user_id;
                END IF;

                IF v_check_role != 'admin' THEN
                    RAISE EXCEPTION
                        '099 VERIFICATION FAILED — admin user (id=%) has role=% (expected admin).',
                        v_admin_user_id, v_check_role;
                END IF;

                IF v_check_super IS NOT TRUE THEN
                    RAISE EXCEPTION
                        '099 VERIFICATION FAILED — admin user (id=%) is_superuser=% (expected TRUE).',
                        v_admin_user_id, v_check_super;
                END IF;

                RAISE NOTICE '099 OK — admin user id=% role=% is_superuser=%',
                    v_admin_user_id, v_check_role, v_check_super;
            END;

        END;
        $$
    """)


def downgrade() -> None:
    """No-op — seed data corrections are not reversible without risk of data loss."""
    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE '099 downgrade — no-op (seed data corrections not reversed automatically)';
        END;
        $$
    """)
