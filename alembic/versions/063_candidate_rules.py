"""063 — DMS VIVANT V2 H2: candidate rules and promotion audit trail.

Stores proposed rule changes derived from patterns/corrections and records
each promotion into config files for traceability and optional rollback.

Revision ID: 063_candidate_rules
Revises    : 062_bitemporal_columns
"""

from alembic import op

revision = "063_candidate_rules"
down_revision = "062_bitemporal_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS public.candidate_rules (
        id                      SERIAL PRIMARY KEY,
        rule_id                 TEXT NOT NULL UNIQUE,
        origin                  TEXT NOT NULL,
        target_config           TEXT NOT NULL,
        change_type             TEXT NOT NULL,
        change_detail           JSONB NOT NULL,
        source_pattern_id       TEXT,
        source_corrections_count INTEGER,
        source_field_path       TEXT,
        status                  TEXT NOT NULL DEFAULT 'proposed',
        proposed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        reviewed_at             TIMESTAMPTZ,
        reviewed_by             TEXT,
        review_notes            TEXT,
        applied_at              TIMESTAMPTZ,
        CONSTRAINT valid_status CHECK (
            status IN ('proposed', 'approved', 'rejected', 'applied')
        )
    );

    CREATE INDEX IF NOT EXISTS idx_candidate_rules_status
        ON public.candidate_rules (status);

    CREATE TABLE IF NOT EXISTS public.rule_promotions (
        id                  SERIAL PRIMARY KEY,
        candidate_rule_id   TEXT NOT NULL
            REFERENCES public.candidate_rules (rule_id),
        promotion_type      TEXT NOT NULL,
        config_file_path    TEXT NOT NULL,
        config_diff         TEXT NOT NULL,
        applied_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        applied_by          TEXT NOT NULL,
        rollback_possible   BOOLEAN DEFAULT TRUE,
        rollback_diff       TEXT
    );
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE IF EXISTS public.rule_promotions;
    DROP TABLE IF EXISTS public.candidate_rules;
    """)
