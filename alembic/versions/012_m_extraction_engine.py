"""M-EXTRACTION-ENGINE
Migration : 012
Dépend de : 011_add_missing_schema (head)
ADR       : ADR-0003 + ADR-0004
Constitution : V3.3.2 §1 (Couche A) + §9 (doctrine échec)

Tables créées :
  - extraction_jobs     (file d'attente OCR asynchrone)
  - extraction_errors   (échecs explicites §9)

Tables modifiées :
  - extractions         (colonnes SLA + méthode)

Triggers :
  - enforce_extraction_job_state_machine
"""

from alembic import op
import sqlalchemy as sa

revision = "012_m_extraction_engine"
down_revision = "011_add_missing_schema"
branch_labels = None
depends_on = None


def upgrade():
    # ── Extension pgcrypto (requise pour gen_random_uuid()) ──────
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── Table extraction_jobs (queue OCR asynchrone SLA-B) ──────
    op.execute("""
        CREATE TABLE IF NOT EXISTS extraction_jobs (
            id              UUID PRIMARY KEY
                                DEFAULT gen_random_uuid(),
            document_id     TEXT NOT NULL
                                REFERENCES documents(id),
            status          VARCHAR NOT NULL DEFAULT 'pending'
                                CHECK (status IN (
                                    'pending',
                                    'processing',
                                    'done',
                                    'failed'
                                )),
            method          VARCHAR NOT NULL
                                CHECK (method IN (
                                    'native_pdf',
                                    'excel_parser',
                                    'docx_parser',
                                    'tesseract',
                                    'azure'
                                )),
            sla_class       VARCHAR NOT NULL
                                CHECK (sla_class IN ('A', 'B')),
            queued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at      TIMESTAMPTZ,
            completed_at    TIMESTAMPTZ,
            duration_ms     INTEGER,
            worker_id       VARCHAR,
            retry_count     INTEGER NOT NULL DEFAULT 0,
            max_retries     INTEGER NOT NULL DEFAULT 3,
            error_message   TEXT
        )
    """)

    # ── Table extraction_errors (§9 doctrine échec explicite) ───
    op.execute("""
        CREATE TABLE IF NOT EXISTS extraction_errors (
            id              UUID PRIMARY KEY
                                DEFAULT gen_random_uuid(),
            document_id     TEXT NOT NULL
                                REFERENCES documents(id),
            job_id          UUID
                                REFERENCES extraction_jobs(id),
            error_code      VARCHAR NOT NULL
                                CHECK (error_code IN (
                                    'UNSUPPORTED_FORMAT',
                                    'CORRUPT_FILE',
                                    'OCR_FAILED',
                                    'TIMEOUT_SLA_A',
                                    'LOW_CONFIDENCE',
                                    'EMPTY_CONTENT',
                                    'PARSE_ERROR'
                                )),
            error_detail    TEXT NOT NULL,
            raw_trace       TEXT,
            requires_human  BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ── Index critiques ──────────────────────────────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extraction_jobs_document_id
            ON extraction_jobs(document_id);

        CREATE INDEX IF NOT EXISTS idx_extraction_jobs_status
            ON extraction_jobs(status);

        CREATE INDEX IF NOT EXISTS idx_extraction_jobs_sla_class
            ON extraction_jobs(sla_class);

        CREATE INDEX IF NOT EXISTS idx_extraction_errors_document_id
            ON extraction_errors(document_id);
    """)

    # ── Trigger machine d'état extraction_jobs ──────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_extraction_job_fsm()
        RETURNS TRIGGER AS $$
        DECLARE
            valid_transitions JSONB := '{
                "pending":    ["processing", "failed"],
                "processing": ["done", "failed"],
                "done":       [],
                "failed":     ["pending"]
            }'::jsonb;
            allowed JSONB;
        BEGIN
            IF OLD.status = NEW.status THEN
                RETURN NEW;
            END IF;

            allowed := valid_transitions -> OLD.status;

            IF NOT (allowed @> to_jsonb(NEW.status)) THEN
                RAISE EXCEPTION
                    'Transition extraction_job invalide : % → % '
                    '(Constitution §8). Autorisées depuis % : %',
                    OLD.status, NEW.status,
                    OLD.status, allowed;
            END IF;

            -- Horodatage automatique selon état
            IF NEW.status = 'processing' THEN
                NEW.started_at := NOW();
            END IF;

            IF NEW.status IN ('done', 'failed') THEN
                NEW.completed_at := NOW();
                IF NEW.started_at IS NOT NULL THEN
                    NEW.duration_ms := EXTRACT(
                        EPOCH FROM (NOW() - NEW.started_at)
                    )::INTEGER * 1000;
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER enforce_extraction_job_fsm_trigger
        BEFORE UPDATE ON extraction_jobs
        FOR EACH ROW
        WHEN (OLD.status IS DISTINCT FROM NEW.status)
        EXECUTE FUNCTION enforce_extraction_job_fsm();
    """)


def downgrade():
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_extraction_job_fsm_trigger
            ON extraction_jobs;
        DROP FUNCTION IF EXISTS enforce_extraction_job_fsm();
        DROP TABLE IF EXISTS extraction_errors;
        DROP TABLE IF EXISTS extraction_jobs;
    """)
