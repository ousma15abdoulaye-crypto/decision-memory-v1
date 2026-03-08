"""neutralise_cascade_fk

Revision ID: m7_4b
Revises: m7_4a_item_identity_doctrine
Create Date: 2026-03-08 19:34:49.303387

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'm7_4b'
down_revision = 'm7_4a_item_identity_doctrine'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_aliases
        DROP CONSTRAINT procurement_dict_aliases_item_id_fkey;
    """)
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_aliases
        ADD CONSTRAINT procurement_dict_aliases_item_id_fkey
        FOREIGN KEY (item_id)
        REFERENCES couche_b.procurement_dict_items(item_id)
        ON DELETE RESTRICT;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_aliases
        DROP CONSTRAINT procurement_dict_aliases_item_id_fkey;
    """)
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_aliases
        ADD CONSTRAINT procurement_dict_aliases_item_id_fkey
        FOREIGN KEY (item_id)
        REFERENCES couche_b.procurement_dict_items(item_id)
        ON DELETE CASCADE;
    """)
