"""Add V1.1 Gate B bundle role fields.

Revision ID: 102_v11_bundle_gate_b_role
Revises: 101_p32_dao_criteria_scoring_schema
Create Date: 2026-04-30

REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "102_v11_bundle_gate_b_role"
down_revision = "101_p32_dao_criteria_scoring_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE supplier_bundles
        ADD COLUMN IF NOT EXISTS gate_b_role TEXT
            CHECK (
                gate_b_role IS NULL
                OR gate_b_role IN (
                    'scorable',
                    'reference',
                    'internal',
                    'unusable'
                )
            )
        """)
    op.execute("""
        ALTER TABLE supplier_bundles
        ADD COLUMN IF NOT EXISTS gate_b_reason_codes TEXT[] NOT NULL DEFAULT '{}'
        """)
    op.execute("""
        ALTER TABLE supplier_bundles
        ADD COLUMN IF NOT EXISTS gate_b_evidence JSONB NOT NULL DEFAULT '[]'::jsonb
        """)
    op.execute("""
        ALTER TABLE supplier_bundles
        ADD COLUMN IF NOT EXISTS gate_b_evaluated_at TIMESTAMPTZ
        """)
    op.execute("""
        ALTER TABLE supplier_bundles
        ADD COLUMN IF NOT EXISTS gate_b_evaluated_by TEXT NOT NULL
            DEFAULT 'bundle_gate_b_service'
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_supplier_bundles_gate_b_role
        ON supplier_bundles(workspace_id, gate_b_role)
        """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_supplier_bundles_gate_b_role")
    op.execute("ALTER TABLE supplier_bundles DROP COLUMN IF EXISTS gate_b_evaluated_by")
    op.execute("ALTER TABLE supplier_bundles DROP COLUMN IF EXISTS gate_b_evaluated_at")
    op.execute("ALTER TABLE supplier_bundles DROP COLUMN IF EXISTS gate_b_evidence")
    op.execute("ALTER TABLE supplier_bundles DROP COLUMN IF EXISTS gate_b_reason_codes")
    op.execute("ALTER TABLE supplier_bundles DROP COLUMN IF EXISTS gate_b_role")
