"""merge heads for single Alembic revision chain

Revision ID: caf949970819
Revises: 009_add_supplier_scoring_tables, 009_supplier_scores_eliminations
Create Date: 2026-02-18 14:26:33.051526

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'caf949970819'
down_revision = ('009_add_supplier_scoring_tables', '009_supplier_scores_eliminations')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
