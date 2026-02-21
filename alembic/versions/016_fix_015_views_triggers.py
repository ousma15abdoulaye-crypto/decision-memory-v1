"""Fix 015 -- create missing view + append-only trigger (CI proof).

Revision ID: 016_fix_015_views_triggers
Revises: 015_m_extraction_corrections
Create Date: 2026-02-21

Intent: DB-level proof. If 015 was previously applied without view/trigger (CI/driver),
this migration enforces the missing artifacts idempotently.
"""

from alembic import op

revision = "016_fix_015_views_triggers"
down_revision = "015_m_extraction_corrections"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_extraction_corrections_append_only()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION
                'VIOLATION INV-6 [table=extraction_corrections op=%] : append-only. Constitution V3.3.2.',
                TG_OP;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        "DROP TRIGGER IF EXISTS trg_extraction_corrections_append_only ON extraction_corrections;"
    )

    op.execute(
        """
        CREATE TRIGGER trg_extraction_corrections_append_only
        BEFORE UPDATE OR DELETE ON extraction_corrections
        FOR EACH ROW EXECUTE FUNCTION enforce_extraction_corrections_append_only()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW structured_data_effective AS
        SELECT DISTINCT ON (e.document_id)
            e.id AS extraction_id,
            e.document_id,
            COALESCE(ec.structured_data, e.structured_data)      AS structured_data,
            COALESCE(ec.confidence_override, e.confidence_score) AS confidence_score,
            e.extraction_method,
            e.extracted_at,
            ec.corrected_at,
            ec.corrected_by,
            ec.correction_reason
        FROM extractions e
        LEFT JOIN LATERAL (
            SELECT *
            FROM extraction_corrections ec2
            WHERE ec2.extraction_id = e.id
            ORDER BY ec2.corrected_at DESC, ec2.id DESC
            LIMIT 1
        ) ec ON true
        ORDER BY e.document_id, e.extracted_at DESC NULLS LAST, e.id
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW extraction_corrections_history AS
        SELECT *
        FROM extraction_corrections
        ORDER BY corrected_at DESC, id
        """
    )


def downgrade():
    op.execute("DROP VIEW IF EXISTS extraction_corrections_history")
    op.execute("DROP VIEW IF EXISTS structured_data_effective")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_extraction_corrections_append_only ON extraction_corrections;"
    )
    op.execute("DROP FUNCTION IF EXISTS enforce_extraction_corrections_append_only()")
