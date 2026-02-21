"""Ensure extraction_jobs and extraction_errors exist (idempotent safety net).

Revision ID: 014_ensure_extraction_tables
Revises: 013_m_extraction_docs
Create Date: 2026-02-20

ADR-0005 §2.1 — filet de sécurité : tables requises par FSM + e2e.
CREATE TABLE IF NOT EXISTS : sans effet si 012 les a déjà créées.
"""
from alembic import op

revision = "014_ensure_extraction_tables"
down_revision = "013_m_extraction_docs"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS extraction_jobs (
            id            VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
            document_id   VARCHAR NOT NULL REFERENCES documents(id),
            status        VARCHAR NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending','running','done','failed')),
            method        VARCHAR NOT NULL
                              CHECK (method IN ('native_pdf','excel_parser','docx_parser','tesseract','azure')),
            sla_class     VARCHAR NOT NULL CHECK (sla_class IN ('A','B')),
            queued_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at    TIMESTAMPTZ,
            completed_at  TIMESTAMPTZ,
            duration_ms   INTEGER,
            worker_id     VARCHAR,
            retry_count   INTEGER NOT NULL DEFAULT 0,
            max_retries   INTEGER NOT NULL DEFAULT 3,
            error_message TEXT
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS extraction_errors (
            id                    VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
            document_id           VARCHAR NOT NULL REFERENCES documents(id),
            job_id                VARCHAR REFERENCES extraction_jobs(id),
            error_code            VARCHAR NOT NULL,
            error_message         TEXT,
            requires_human_review BOOLEAN NOT NULL DEFAULT TRUE,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS extraction_errors")
    op.execute("DROP TABLE IF EXISTS extraction_jobs")
