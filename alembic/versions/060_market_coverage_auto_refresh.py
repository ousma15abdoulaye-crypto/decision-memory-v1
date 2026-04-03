"""060 — Auto-refresh market_coverage matview on market_signals_v2 INSERT.

Trigger AFTER INSERT ON market_signals_v2 FOR EACH STATEMENT refreshes
the materialized view concurrently.  Exception is caught so the INSERT
is never blocked by a refresh failure.

Pré-requis : unique index idx_market_coverage_pk on (item_id, zone_id) — migration 042.

Revision ID: 060_market_coverage_auto_refresh
Revises    : 059_m14_score_history_elimination_log
"""

from alembic import op

revision = "060_market_coverage_auto_refresh"
down_revision = "059_m14_score_history_elimination_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
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

    op.execute(
        "DROP TRIGGER IF EXISTS trg_refresh_market_coverage ON public.market_signals_v2;"
    )
    op.execute("""
    CREATE TRIGGER trg_refresh_market_coverage
        AFTER INSERT ON public.market_signals_v2
        FOR EACH STATEMENT
        EXECUTE FUNCTION fn_refresh_market_coverage();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_refresh_market_coverage ON public.market_signals_v2;"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_refresh_market_coverage();")
