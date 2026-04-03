"""064 — DMS VIVANT V2 H3: embeddings table with pgvector.

Stores dense (vector(1024)) and sparse (JSONB) embeddings for RAG retrieval.
IVFFlat index created separately after initial batch load.

Revision ID: 064_dms_embeddings
Revises    : 063_candidate_rules
"""

from alembic import op

revision = "064_dms_embeddings"
down_revision = "063_candidate_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS public.dms_embeddings (
        id              BIGSERIAL PRIMARY KEY,
        source_table    TEXT NOT NULL,
        source_pk       BIGINT NOT NULL,
        chunk_index     INTEGER NOT NULL DEFAULT 0,
        chunk_text      TEXT NOT NULL,
        embedding_dense vector(1024) NOT NULL,
        embedding_sparse JSONB NOT NULL DEFAULT '{}',
        model_name      TEXT NOT NULL DEFAULT 'bge-m3',
        model_version   TEXT NOT NULL DEFAULT '1.0',
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (source_table, source_pk, chunk_index)
    );

    CREATE INDEX IF NOT EXISTS idx_embeddings_source
        ON public.dms_embeddings (source_table, source_pk);

    CREATE INDEX IF NOT EXISTS idx_embeddings_model
        ON public.dms_embeddings (model_name);
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE IF EXISTS public.dms_embeddings CASCADE;
    """)
