"""085 — M16 index pour requêtes cadre / projection

Revision ID: 085_m16_frame_query_indexes
Revises: 084_m16_price_line_comparisons

REGLE-12 : op.execute() SQL brut. Downgrade obligatoire.
"""

from __future__ import annotations

from alembic import op

revision = "085_m16_frame_query_indexes"
down_revision = "084_m16_price_line_comparisons"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ca_workspace_bundle
        ON criterion_assessments(workspace_id, bundle_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_plbv_workspace_bundle
        ON price_line_bundle_values(workspace_id, bundle_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_plbv_workspace_bundle")
    op.execute("DROP INDEX IF EXISTS idx_ca_workspace_bundle")
