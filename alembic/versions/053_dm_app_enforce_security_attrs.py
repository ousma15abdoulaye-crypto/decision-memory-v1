"""053 — Re-applique les attributs de sécurité sur dm_app (déploiements ayant déjà passé 052 sans ALTER).

Revision ID: 053_dm_app_enforce_security_attrs
Revises: 052_dm_app_rls_role
"""

from alembic import op

revision = "053_dm_app_enforce_security_attrs"
down_revision = "052_dm_app_rls_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dm_app') THEN
            EXECUTE 'ALTER ROLE dm_app NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS';
          END IF;
        END
        $$;
    """)


def downgrade() -> None:
    pass
