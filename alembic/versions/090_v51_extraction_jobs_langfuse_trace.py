"""090 — V5.1 extraction_jobs.langfuse_trace_id

Revision ID: 090_v51_extraction_jobs_langfuse_trace
Revises: 089_v51_rls_force_corrective

REGLE-12 : op.execute() SQL brut. Downgrade obligatoire.
Canon V5.1.0 Section 9.4 — INV-A01 : tout appel LLM d'extraction est tracé.
"""

from __future__ import annotations

from alembic import op

revision = "090_v51_extraction_jobs_langfuse_trace"
down_revision = "089_v51_rls_force_corrective"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE extraction_jobs
        ADD COLUMN IF NOT EXISTS langfuse_trace_id VARCHAR(100)
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE extraction_jobs
        DROP COLUMN IF EXISTS langfuse_trace_id
    """)
