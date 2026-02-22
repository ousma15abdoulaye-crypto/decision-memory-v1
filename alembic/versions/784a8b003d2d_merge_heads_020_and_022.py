"""merge heads 020 and 022

Revision ID: 784a8b003d2d
Revises: 020_m_criteria_typing, 022_seed_dict_sahel
Create Date: 2026-02-22 05:23:44.634732

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '784a8b003d2d'
down_revision = ('020_m_criteria_typing', '022_seed_dict_sahel')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
