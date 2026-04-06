"""080 - index market_signals_v2(zone_id) for PV MSv2 fallback lookups

Revision ID: 080_market_signals_v2_zone_id_index
Revises: 079_bloc5_confidence_qualification_signal_log
Create Date: 2026-04-06

Supports build_pv_snapshot fallback SELECT filtered by zone_id (DMS-FIX-VMS-PIPELINE-V001).
REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "080_market_signals_v2_zone_id_index"
down_revision = "079_bloc5_confidence_qualification_signal_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_msv2_zone_id
        ON public.market_signals_v2(zone_id)
        """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.idx_msv2_zone_id")
