"""024 -- M-PARSING-MERCURIALE: table couche_b.mercuriale_raw_queue"""

from alembic import op

revision = "024_mercuriale_raw_queue"
down_revision = "023_m_criteria_fk"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_b.mercuriale_raw_queue (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            raw_line        TEXT        NOT NULL,
            source          TEXT        NULL,
            imported_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            parse_status    TEXT        NULL
                CONSTRAINT chk_mercuriale_parse_status
                CHECK (parse_status IN ('pending','ok','partial','unparseable')),
            designation_raw TEXT        NULL,
            unite_raw       TEXT        NULL,
            price_min       NUMERIC(18,4) NULL,
            price_avg       NUMERIC(18,4) NULL,
            price_max       NUMERIC(18,4) NULL,
            currency        TEXT        NOT NULL DEFAULT 'XOF',
            item_id         TEXT        NULL
                REFERENCES couche_b.procurement_dict_items(item_id)
                ON DELETE SET NULL,
            strategy        TEXT        NULL,
            score           NUMERIC(6,3) NULL,
            parse_errors    JSONB       NOT NULL DEFAULT '[]'::jsonb
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mercuriale_raw_queue_item_id
            ON couche_b.mercuriale_raw_queue(item_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mercuriale_raw_queue_parse_status
            ON couche_b.mercuriale_raw_queue(parse_status);
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS couche_b.idx_mercuriale_raw_queue_parse_status;
    """)
    op.execute("""
        DROP INDEX IF EXISTS couche_b.idx_mercuriale_raw_queue_item_id;
    """)
    op.execute("""
        DROP TABLE IF EXISTS couche_b.mercuriale_raw_queue;
    """)
