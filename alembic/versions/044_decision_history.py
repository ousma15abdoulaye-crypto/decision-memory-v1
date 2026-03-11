"""
044 - decision_history — source signal 0.15

Revision : 044_decision_history
Down     : 043_market_signals_v11
"""

from alembic import op

revision = "044_decision_history"
down_revision = "043_market_signals_v11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.decision_history (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            item_id           TEXT NOT NULL
                              REFERENCES couche_b.procurement_dict_items(item_id),
            zone_id           TEXT NOT NULL,
            decision_type     TEXT NOT NULL,
            unit_price        NUMERIC(15,2) NOT NULL,
            quantity          NUMERIC(15,2),
            currency          TEXT NOT NULL DEFAULT 'XOF',
            decided_at        DATE NOT NULL,
            source_ref        TEXT,
            org_id            TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.create_index(
        "ix_decision_history_item_zone",
        "decision_history",
        ["item_id", "zone_id"],
        schema="public",
    )
    op.create_index(
        "ix_decision_history_decided_at",
        "decision_history",
        ["decided_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_decision_history_decided_at",
        table_name="decision_history",
        schema="public",
    )
    op.drop_index(
        "ix_decision_history_item_zone",
        table_name="decision_history",
        schema="public",
    )
    op.drop_table("decision_history", schema="public")
