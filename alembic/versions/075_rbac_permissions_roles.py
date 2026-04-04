"""075 - RBAC V4.2.0 : permissions, roles, role_permissions, user_tenant_roles (V4.2.0)

Revision ID: 075_rbac_permissions_roles
Revises: 074_drop_case_id_set_workspace_not_null
Create Date: 2026-04-04

Cree le systeme RBAC V4.2.0 :
  - rbac_permissions    : 17 permissions atomiques
  - rbac_roles          : 6 roles pilote SCI Mali
  - rbac_role_permissions : matrice role <-> permission
  - user_tenant_roles   : affectation utilisateur <-> role <-> tenant

Migration des utilisateurs existants V4.1.0 :
  - superuser/admin -> 'procurement_director'
  - procurement_officer -> 'procurement_officer'
  - viewer -> 'market_analyst'

Reference : docs/freeze/DMS_V4.2.0_RBAC.md
users.id = INTEGER (migration 004 reelle).
REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "075_rbac_permissions_roles"
down_revision = "074_drop_case_id_set_workspace_not_null"
branch_labels = None
depends_on = None

_PERMISSIONS = [
    ("workspace.create", "workspaces", "Créer un workspace"),
    ("workspace.read", "workspaces", "Lire un workspace"),
    ("workspace.update", "workspaces", "Modifier un workspace"),
    ("workspace.close", "workspaces", "Clôturer un workspace"),
    ("workspace.seal_override", "workspaces", "Sceller d'urgence (admin)"),
    ("bundle.upload", "bundles", "Uploader un ZIP fournisseur"),
    ("bundle.validate", "bundles", "Valider un bundle HITL"),
    ("bundle.read", "bundles", "Lire les bundles"),
    ("committee.manage", "committee", "Gérer la session comité"),
    ("committee.vote", "committee", "Participer au vote"),
    ("committee.observe", "committee", "Observer la délibération"),
    ("market.read", "market", "Lire les données marché"),
    ("market.annotate", "market", "Annoter les signaux marché"),
    ("market.watchlist", "market", "Gérer la liste de surveillance"),
    ("admin.tenant", "admin", "Gérer les tenants"),
    ("admin.users", "admin", "Gérer les utilisateurs"),
    ("admin.export", "admin", "Exporter les données"),
]

_ROLES = [
    ("procurement_director", "Directeur achats SCI Mali — accès total processus"),
    ("procurement_officer", "Agent achats — gestion workspace quotidien"),
    ("committee_chair", "Président comité — clôture délibération"),
    ("committee_member", "Membre comité — vote uniquement"),
    ("market_analyst", "Analyste marché — lecture + annotation marché"),
    ("supply_chain_admin", "Admin supply chain — gestion utilisateurs"),
]

_ROLE_PERMISSIONS = {
    "procurement_director": [
        "workspace.create",
        "workspace.read",
        "workspace.update",
        "workspace.close",
        "bundle.upload",
        "bundle.validate",
        "bundle.read",
        "committee.manage",
        "committee.observe",
        "market.read",
        "market.annotate",
        "market.watchlist",
    ],
    "procurement_officer": [
        "workspace.create",
        "workspace.read",
        "workspace.update",
        "bundle.upload",
        "bundle.read",
        "committee.observe",
        "market.read",
    ],
    "committee_chair": [
        "workspace.read",
        "committee.manage",
        "committee.vote",
        "committee.observe",
        "bundle.read",
        "market.read",
    ],
    "committee_member": [
        "workspace.read",
        "committee.vote",
        "committee.observe",
        "bundle.read",
        "market.read",
    ],
    "market_analyst": [
        "workspace.read",
        "bundle.read",
        "committee.observe",
        "market.read",
        "market.annotate",
        "market.watchlist",
    ],
    "supply_chain_admin": [
        "workspace.create",
        "workspace.read",
        "workspace.update",
        "workspace.close",
        "workspace.seal_override",
        "bundle.upload",
        "bundle.validate",
        "bundle.read",
        "committee.manage",
        "committee.vote",
        "committee.observe",
        "market.read",
        "market.annotate",
        "market.watchlist",
        "admin.tenant",
        "admin.users",
        "admin.export",
    ],
}


def upgrade() -> None:
    op.execute("""
        CREATE TABLE rbac_permissions (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code        TEXT NOT NULL UNIQUE,
            resource    TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

    op.execute("""
        CREATE TABLE rbac_roles (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code        TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            is_system   BOOLEAN NOT NULL DEFAULT FALSE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

    op.execute("""
        CREATE TABLE rbac_role_permissions (
            role_id       UUID NOT NULL REFERENCES rbac_roles(id) ON DELETE CASCADE,
            permission_id UUID NOT NULL REFERENCES rbac_permissions(id) ON DELETE CASCADE,
            PRIMARY KEY (role_id, permission_id)
        )
        """)

    op.execute("""
        CREATE TABLE user_tenant_roles (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id    INTEGER NOT NULL REFERENCES users(id),
            tenant_id  UUID NOT NULL REFERENCES tenants(id),
            role_id    UUID NOT NULL REFERENCES rbac_roles(id),
            granted_by INTEGER REFERENCES users(id),
            granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMPTZ,
            UNIQUE (user_id, tenant_id, role_id)
        )
        """)

    op.execute("ALTER TABLE user_tenant_roles ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY utr_tenant_isolation ON user_tenant_roles
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    for code, resource, description in _PERMISSIONS:
        op.execute(f"""
            INSERT INTO rbac_permissions (code, resource, description)
            VALUES ('{code}', '{resource}', '{description.replace("'", "''")}')
            ON CONFLICT (code) DO NOTHING
            """)

    for code, description in _ROLES:
        op.execute(f"""
            INSERT INTO rbac_roles (code, description, is_system)
            VALUES ('{code}', '{description.replace("'", "''")}', TRUE)
            ON CONFLICT (code) DO NOTHING
            """)

    for role_code, perms in _ROLE_PERMISSIONS.items():
        for perm_code in perms:
            op.execute(f"""
                INSERT INTO rbac_role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM rbac_roles r, rbac_permissions p
                WHERE r.code = '{role_code}' AND p.code = '{perm_code}'
                ON CONFLICT DO NOTHING
                """)

    op.execute("""
        INSERT INTO user_tenant_roles (user_id, tenant_id, role_id)
        SELECT u.id, t.id, r.id
        FROM users u
        CROSS JOIN tenants t
        CROSS JOIN rbac_roles r
        WHERE u.is_superuser = TRUE
          AND r.code = 'supply_chain_admin'
        ON CONFLICT DO NOTHING
        """)

    op.execute("""
        INSERT INTO user_tenant_roles (user_id, tenant_id, role_id)
        SELECT u.id, t.id, r.id
        FROM users u
        JOIN roles old_r ON old_r.id = u.role_id
        CROSS JOIN tenants t
        CROSS JOIN rbac_roles r
        WHERE u.is_superuser = FALSE
          AND old_r.name = 'procurement_officer'
          AND r.code = 'procurement_officer'
        ON CONFLICT DO NOTHING
        """)

    op.execute("""
        INSERT INTO user_tenant_roles (user_id, tenant_id, role_id)
        SELECT u.id, t.id, r.id
        FROM users u
        JOIN roles old_r ON old_r.id = u.role_id
        CROSS JOIN tenants t
        CROSS JOIN rbac_roles r
        WHERE u.is_superuser = FALSE
          AND old_r.name = 'viewer'
          AND r.code = 'market_analyst'
        ON CONFLICT DO NOTHING
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_tenant_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS rbac_role_permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS rbac_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS rbac_permissions CASCADE")
