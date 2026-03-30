"""054 — M12 correction log: append-only feedback loop table.

Captures human corrections to M12 recognition outputs.
Append-only: no UPDATE, no DELETE. Used by the feedback loop to suggest
pattern/signal enrichment (human validation required before commit).

Revision ID: 054_m12_correction_log
Revises: 053_dm_app_enforce_security_attrs
"""

from alembic import op

revision = "054_m12_correction_log"
down_revision = "053_dm_app_enforce_security_attrs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS m12_correction_log (
        id              BIGSERIAL       PRIMARY KEY,
        document_id     TEXT            NOT NULL,
        run_id          UUID            NOT NULL,
        correction_type TEXT            NOT NULL
            CHECK (correction_type IN (
                'framework', 'family', 'document_kind', 'subtype',
                'validity', 'conformity', 'process_link', 'other'
            )),
        field_corrected TEXT            NOT NULL,
        original_value  JSONB           NOT NULL DEFAULT '{}',
        corrected_value JSONB           NOT NULL DEFAULT '{}',
        corrected_by    TEXT            NOT NULL DEFAULT 'human_annotator',
        correction_note TEXT,
        created_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
    );

    COMMENT ON TABLE m12_correction_log
        IS 'Append-only M12 human corrections — feedback loop for signal enrichment';

    CREATE INDEX idx_m12_corr_doc_id ON m12_correction_log (document_id);
    CREATE INDEX idx_m12_corr_type   ON m12_correction_log (correction_type);
    CREATE INDEX idx_m12_corr_date   ON m12_correction_log (created_at);

    -- Append-only: trigger prevents UPDATE and DELETE
    CREATE OR REPLACE FUNCTION m12_correction_log_no_modify()
        RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'm12_correction_log is append-only: % not allowed', TG_OP;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_m12_correction_log_no_update
        BEFORE UPDATE ON m12_correction_log
        FOR EACH ROW EXECUTE FUNCTION m12_correction_log_no_modify();

    CREATE TRIGGER trg_m12_correction_log_no_delete
        BEFORE DELETE ON m12_correction_log
        FOR EACH ROW EXECUTE FUNCTION m12_correction_log_no_modify();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TRIGGER IF EXISTS trg_m12_correction_log_no_delete ON m12_correction_log;
    DROP TRIGGER IF EXISTS trg_m12_correction_log_no_update ON m12_correction_log;
    DROP FUNCTION IF EXISTS m12_correction_log_no_modify();
    DROP TABLE IF EXISTS m12_correction_log;
    """)
