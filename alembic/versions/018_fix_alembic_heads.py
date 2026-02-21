"""Fix Alembic heads — single linear chain after 016.

Revision ID: 018_fix_alembic_heads
Revises: 016_fix_015_views_triggers
Create Date: 2026-02-21

Purpose: Replace corrupted 017/caf merge with clean single head.
"""

from alembic import op

revision = "018_fix_alembic_heads"
down_revision = "016_fix_015_views_triggers"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
