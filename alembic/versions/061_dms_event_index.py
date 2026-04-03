"""061 — DMS VIVANT V2 H2: append-only event index (partitioned by ingestion_time).

Central index for domain events: one row per logical event, partitioned for
retention and query pruning. UPDATE/DELETE blocked at trigger level.

PostgreSQL partitioned tables require UNIQUE indexes to include the partition
key; ``event_id``, idempotency, and aggregate-version uniques therefore use
``ingestion_time`` as a trailing column (see indexes below).

Revision ID: 061_dms_event_index
Revises    : 060_market_coverage_auto_refresh
"""

from alembic import op

revision = "061_dms_event_index"
down_revision = "060_market_coverage_auto_refresh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE public.dms_event_index (
        id                 BIGSERIAL,
        event_id           UUID NOT NULL DEFAULT gen_random_uuid(),
        event_domain       TEXT NOT NULL,
        source_table       TEXT NOT NULL,
        source_pk          BIGINT NOT NULL,
        case_id            TEXT,
        supplier_id        TEXT,
        item_id            TEXT,
        document_id        TEXT,
        aggregate_type     TEXT NOT NULL,
        aggregate_id       TEXT,
        event_type         TEXT NOT NULL,
        aggregate_version  BIGINT,
        idempotency_key    TEXT,
        event_time         TIMESTAMPTZ NOT NULL,
        ingestion_time     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        summary            JSONB NOT NULL DEFAULT '{}',
        source_hash        TEXT,
        schema_version     TEXT NOT NULL DEFAULT '1.0',
        PRIMARY KEY (id, ingestion_time)
    ) PARTITION BY RANGE (ingestion_time);

    CREATE TABLE public.dms_event_index_2025_h2 PARTITION OF public.dms_event_index
        FOR VALUES FROM ('2025-07-01') TO ('2027-01-01');

    CREATE UNIQUE INDEX idx_event_event_id
        ON public.dms_event_index (event_id, ingestion_time);

    CREATE INDEX idx_event_case
        ON public.dms_event_index (case_id, event_time)
        WHERE case_id IS NOT NULL;

    CREATE INDEX idx_event_type
        ON public.dms_event_index (event_type, event_time);

    CREATE INDEX idx_event_domain
        ON public.dms_event_index (event_domain, event_time);

    CREATE UNIQUE INDEX idx_event_source
        ON public.dms_event_index (source_table, source_pk, ingestion_time);

    CREATE UNIQUE INDEX idx_event_aggregate_version
        ON public.dms_event_index (aggregate_type, aggregate_id, aggregate_version, ingestion_time)
        WHERE aggregate_version IS NOT NULL;

    CREATE UNIQUE INDEX idx_event_idempotency
        ON public.dms_event_index (idempotency_key, ingestion_time)
        WHERE idempotency_key IS NOT NULL;

    CREATE INDEX idx_event_summary
        ON public.dms_event_index USING GIN (summary jsonb_path_ops);

    CREATE OR REPLACE FUNCTION public.dms_event_index_no_modify()
        RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'dms_event_index is append-only: % not allowed', TG_OP;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trg_event_index_no_update ON public.dms_event_index;
    CREATE TRIGGER trg_event_index_no_update
        BEFORE UPDATE ON public.dms_event_index
        FOR EACH ROW EXECUTE FUNCTION public.dms_event_index_no_modify();

    DROP TRIGGER IF EXISTS trg_event_index_no_delete ON public.dms_event_index;
    CREATE TRIGGER trg_event_index_no_delete
        BEFORE DELETE ON public.dms_event_index
        FOR EACH ROW EXECUTE FUNCTION public.dms_event_index_no_modify();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TRIGGER IF EXISTS trg_event_index_no_delete ON public.dms_event_index;
    DROP TRIGGER IF EXISTS trg_event_index_no_update ON public.dms_event_index;
    DROP FUNCTION IF EXISTS public.dms_event_index_no_modify();
    DROP TABLE IF EXISTS public.dms_event_index CASCADE;
    """)
