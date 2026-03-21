"""052 — rôle applicatif dm_app (NOBYPASSRLS) + GRANTs pour tests RLS.

Révision : 051_cases_tenant_user_tenants_rls

Le mot de passe LOGIN n'est pas posé ici : en CI, exécuter après upgrade :
  ALTER ROLE dm_app WITH LOGIN PASSWORD '...';

Revision ID: 052_dm_app_rls_role
Revises: 051_cases_tenant_user_tenants_rls
"""

from alembic import op

revision = "052_dm_app_rls_role"
down_revision = "051_cases_tenant_user_tenants_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dm_app') THEN
            CREATE ROLE dm_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
          END IF;
        END
        $$;
    """)
    # Attributs de sécurité même si le rôle préexistait (BYPASSRLS / SUPERUSER manuels)
    op.execute(
        "ALTER ROLE dm_app NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;"
    )
    op.execute("""
        DO $$
        DECLARE dbname text;
        BEGIN
          SELECT current_database() INTO dbname;
          EXECUTE format('GRANT CONNECT ON DATABASE %I TO dm_app', dbname);
        END
        $$;
    """)
    op.execute("GRANT USAGE ON SCHEMA public TO dm_app;")
    op.execute("""
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'couche_b') THEN
            EXECUTE 'GRANT USAGE ON SCHEMA couche_b TO dm_app';
            EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA couche_b TO dm_app';
            EXECUTE 'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA couche_b TO dm_app';
          END IF;
        END
        $$;
        """)
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dm_app;"
    )
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dm_app;")
    op.execute("""
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO dm_app;
        """)
    op.execute("""
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO dm_app;
        """)


def downgrade() -> None:
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM dm_app;")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM dm_app;")
    op.execute("REVOKE USAGE ON SCHEMA public FROM dm_app;")
    op.execute("""
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'couche_b') THEN
            EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA couche_b FROM dm_app';
            EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA couche_b FROM dm_app';
            EXECUTE 'REVOKE USAGE ON SCHEMA couche_b FROM dm_app';
          END IF;
        END
        $$;
        """)
    op.execute("""
        DO $$
        DECLARE dbname text;
        BEGIN
          SELECT current_database() INTO dbname;
          EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM dm_app', dbname);
        END
        $$;
        """)
    op.execute("DROP ROLE IF EXISTS dm_app;")
