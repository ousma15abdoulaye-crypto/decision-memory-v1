"""068 - Create tenants table (V4.2.0 Migration A)

Revision ID: 068_create_tenants
Revises: 067_fix_market_coverage_trigger
Create Date: 2026-04-04

Premiere migration V4.2.0 Workspace-First.
Cree la table tenants — reference globale pour l'isolation multi-tenant.
RLS non activee sur cette table (filtree applicativement).

Reference : docs/freeze/DMS_V4.2.0_SCHEMA.sql lignes 20-26
REGLE-12 : op.execute() uniquement — pas d'autogenerate.
"""

from __future__ import annotations

from alembic import op

revision = "068_create_tenants"
down_revision = "067_fix_market_coverage_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE tenants (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code       TEXT NOT NULL UNIQUE,
            name       TEXT NOT NULL,
            is_active  BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

    op.execute("""
        INSERT INTO tenants (code, name)
        VALUES ('sci_mali', 'Save the Children Mali')
        ON CONFLICT (code) DO NOTHING
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenants CASCADE")
