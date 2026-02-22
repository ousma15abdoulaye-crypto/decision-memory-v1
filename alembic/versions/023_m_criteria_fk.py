"""023 -- M-CRITERIA-FK: FK canonical_item_id -> Couche B"""
from alembic import op

revision      = "023_m_criteria_fk"
down_revision = "784a8b003d2d"
branch_labels = None
depends_on    = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_criteria_canonical_item'
            ) THEN
                ALTER TABLE public.criteria
                  ADD CONSTRAINT fk_criteria_canonical_item
                  FOREIGN KEY (canonical_item_id)
                  REFERENCES couche_b.procurement_dict_items(item_id)
                  ON DELETE RESTRICT;
            END IF;
        END $$;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_criteria_canonical_item_id
          ON public.criteria(canonical_item_id);
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS public.idx_criteria_canonical_item_id;
    """)
    op.execute("""
        ALTER TABLE public.criteria
          DROP CONSTRAINT IF EXISTS fk_criteria_canonical_item;
    """)
