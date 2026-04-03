"""065 — DMS VIVANT V2 H3: LLM trace table (Langfuse backup).

Append-only local backup of every LLM call: model, tokens, latency, cost.
Mirrors Langfuse traces for offline analysis and audit.

Revision ID: 065_llm_traces
Revises    : 064_dms_embeddings
"""

from alembic import op

revision = "065_llm_traces"
down_revision = "064_dms_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE public.llm_traces (
        id              BIGSERIAL PRIMARY KEY,
        trace_id        UUID NOT NULL DEFAULT gen_random_uuid(),
        span_id         TEXT,
        parent_span_id  TEXT,
        operation       TEXT NOT NULL,
        model_name      TEXT NOT NULL,
        provider        TEXT NOT NULL DEFAULT 'openrouter',
        input_tokens    INTEGER NOT NULL DEFAULT 0,
        output_tokens   INTEGER NOT NULL DEFAULT 0,
        total_tokens    INTEGER NOT NULL DEFAULT 0,
        latency_ms      INTEGER NOT NULL DEFAULT 0,
        cost_usd        NUMERIC(10, 6) NOT NULL DEFAULT 0,
        status          TEXT NOT NULL DEFAULT 'success',
        error_message   TEXT,
        metadata        JSONB NOT NULL DEFAULT '{}',
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (trace_id)
    );

    CREATE INDEX idx_llm_traces_operation
        ON public.llm_traces (operation, created_at);

    CREATE INDEX idx_llm_traces_model
        ON public.llm_traces (model_name, created_at);

    CREATE INDEX idx_llm_traces_status
        ON public.llm_traces (status)
        WHERE status <> 'success';
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE IF EXISTS public.llm_traces CASCADE;
    """)
