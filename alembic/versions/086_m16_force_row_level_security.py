"""086 — M16 FORCE ROW LEVEL SECURITY sur tables du périmètre comparatif

Revision ID: 086_m16_force_row_level_security
Revises: 085_m16_frame_query_indexes

REGLE-12 : op.execute() SQL brut. Downgrade obligatoire.
"""

from __future__ import annotations

from alembic import op

revision = "086_m16_force_row_level_security"
down_revision = "085_m16_frame_query_indexes"
branch_labels = None
depends_on = None

M16_TABLES = (
    "evaluation_domains",
    "criterion_assessments",
    "deliberation_threads",
    "deliberation_messages",
    "clarification_requests",
    "criterion_assessment_history",
    "validated_analytical_notes",
    "price_line_comparisons",
    "price_line_bundle_values",
)


def upgrade() -> None:
    for table in M16_TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in reversed(M16_TABLES):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
