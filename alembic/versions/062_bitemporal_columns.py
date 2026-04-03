"""062 — DMS VIVANT V2 H2: bitemporal ``event_time`` on core tables.

Adds ``event_time`` (valid-time / business time) alongside ``created_at``
(system time) on correction log, snapshots, market signals, and decision
history. Existing rows are backfilled from ``created_at``.

Revision ID: 062_bitemporal_columns
Revises    : 061_dms_event_index
"""

from alembic import op

revision = "062_bitemporal_columns"
down_revision = "061_dms_event_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE public.m12_correction_log
        ADD COLUMN event_time TIMESTAMPTZ;

    UPDATE public.m12_correction_log
    SET event_time = created_at
    WHERE event_time IS NULL;

    ALTER TABLE public.m12_correction_log
        ALTER COLUMN event_time SET NOT NULL;

    ALTER TABLE public.decision_snapshots
        ADD COLUMN event_time TIMESTAMPTZ;

    UPDATE public.decision_snapshots
    SET event_time = created_at
    WHERE event_time IS NULL;

    ALTER TABLE public.decision_snapshots
        ALTER COLUMN event_time SET NOT NULL;

    ALTER TABLE public.market_signals_v2
        ADD COLUMN event_time TIMESTAMPTZ;

    UPDATE public.market_signals_v2
    SET event_time = created_at
    WHERE event_time IS NULL;

    ALTER TABLE public.market_signals_v2
        ALTER COLUMN event_time SET NOT NULL;

    ALTER TABLE public.decision_history
        ADD COLUMN event_time TIMESTAMPTZ;

    UPDATE public.decision_history
    SET event_time = created_at
    WHERE event_time IS NULL;

    ALTER TABLE public.decision_history
        ALTER COLUMN event_time SET NOT NULL;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE public.m12_correction_log DROP COLUMN IF EXISTS event_time;
    ALTER TABLE public.decision_snapshots DROP COLUMN IF EXISTS event_time;
    ALTER TABLE public.market_signals_v2 DROP COLUMN IF EXISTS event_time;
    ALTER TABLE public.decision_history DROP COLUMN IF EXISTS event_time;
    """)
