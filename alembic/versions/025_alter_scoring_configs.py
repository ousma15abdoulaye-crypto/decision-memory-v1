"""025 -- M-SCORING-ENGINE: add price_ratio columns to scoring_configs"""

from alembic import op

revision = "025_alter_scoring_configs"
down_revision = "024_mercuriale_raw_queue"
branch_labels = None
depends_on = None


def upgrade():
    # Add price_ratio_acceptable (default 1.05 = 5% above ref is OK)
    op.execute("""
        ALTER TABLE public.scoring_configs
          ADD COLUMN IF NOT EXISTS price_ratio_acceptable DOUBLE PRECISION
              NOT NULL DEFAULT 1.05;
    """)
    # Add price_ratio_eleve (default 1.20 = 20% above ref = high)
    op.execute("""
        ALTER TABLE public.scoring_configs
          ADD COLUMN IF NOT EXISTS price_ratio_eleve DOUBLE PRECISION
              NOT NULL DEFAULT 1.20;
    """)
    # Add CHECK constraint if absent
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'chk_scoring_configs_ratios'
            ) THEN
                ALTER TABLE public.scoring_configs
                  ADD CONSTRAINT chk_scoring_configs_ratios
                  CHECK (price_ratio_acceptable < price_ratio_eleve);
            END IF;
        END $$;
    """)
    # Add UNIQUE on profile_code if absent
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_scoring_configs_profile_code'
            ) THEN
                ALTER TABLE public.scoring_configs
                  ADD CONSTRAINT uq_scoring_configs_profile_code
                  UNIQUE (profile_code);
            END IF;
        END $$;
    """)
    # Seed GENERIC if absent
    op.execute("""
        INSERT INTO public.scoring_configs (
            id, profile_code, commercial_formula, commercial_weight,
            capacity_formula, capacity_weight,
            sustainability_formula, sustainability_weight,
            essentials_weight, price_ratio_acceptable, price_ratio_eleve,
            created_at, updated_at
        )
        VALUES (
            'scoring_generic', 'GENERIC', 'price_lowest_100', 0.5,
            'capacity_experience', 0.3,
            'sustainability_certifications', 0.1,
            0.0, 1.05, 1.20,
            '2026-02-22T00:00:00Z', '2026-02-22T00:00:00Z'
        )
        ON CONFLICT (id) DO UPDATE
          SET price_ratio_acceptable = EXCLUDED.price_ratio_acceptable,
              price_ratio_eleve      = EXCLUDED.price_ratio_eleve;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE public.scoring_configs
          DROP CONSTRAINT IF EXISTS chk_scoring_configs_ratios;
    """)
    op.execute("""
        ALTER TABLE public.scoring_configs
          DROP CONSTRAINT IF EXISTS uq_scoring_configs_profile_code;
    """)
    op.execute("""
        ALTER TABLE public.scoring_configs
          DROP COLUMN IF EXISTS price_ratio_acceptable;
    """)
    op.execute("""
        ALTER TABLE public.scoring_configs
          DROP COLUMN IF EXISTS price_ratio_eleve;
    """)
