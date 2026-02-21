"""Merge Alembic heads: caf949... + 016_fix_015_views_triggers.

Revision ID: 017_merge_heads_caf_016
Revises: caf949970819_merge_heads_for_single_alembic_revision_, 016_fix_015_views_triggers
Create Date: 2026-02-21

Purpose: unify heads so CI applies 014/015/016 lineage and DB objects exist (views + triggers).
"""

from alembic import op

revision = "017_merge_heads_caf_016"
down_revision = (
    "caf949970819_merge_heads_for_single_alembic_revision_",
    "016_fix_015_views_triggers",
)
branch_labels = None
depends_on = None


def upgrade():
    # merge-only revision (no-op)
    pass


def downgrade():
    # merge-only revision (no-op)
    pass
