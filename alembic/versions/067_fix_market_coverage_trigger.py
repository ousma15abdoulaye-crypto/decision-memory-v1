"""067 — Fix market_coverage refresh trigger: drop CONCURRENTLY.

``REFRESH MATERIALIZED VIEW CONCURRENTLY`` cannot run inside a transaction
block.  A trigger function always executes within the INSERT transaction, so
migration 060's implementation always falls through to the EXCEPTION handler
and emits a WARNING — ``market_coverage`` is never actually refreshed.

This migration replaces the trigger function with a non-concurrent refresh.
The share-update-exclusive lock acquired by non-concurrent REFRESH is
acceptable: the refresh is fast (small matview) and the INSERT already holds
a row-level lock on ``market_signals_v2``.

Fixes: Copilot review comment on PR #300 (alembic/versions/060…:30).

Revision ID: 067_fix_market_coverage_trigger
Revises    : 066_bridge_triggers
"""

from alembic import op

revision = "067_fix_market_coverage_trigger"
down_revision = "066_bridge_triggers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION fn_refresh_market_coverage()
    RETURNS TRIGGER AS $$
    BEGIN
        BEGIN
            REFRESH MATERIALIZED VIEW public.market_coverage;
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'market_coverage refresh failed: %', SQLERRM;
        END;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION fn_refresh_market_coverage()
    RETURNS TRIGGER AS $$
    BEGIN
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY public.market_coverage;
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'market_coverage refresh failed: %', SQLERRM;
        END;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """)
