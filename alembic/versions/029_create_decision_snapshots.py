"""029 -- decision_snapshots append-only (ADR-0011: capture tôt, agrégation tard)."""

from alembic import op

revision = "029_create_decision_snapshots"
down_revision = "028_create_committee_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.decision_snapshots (
            snapshot_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id              TEXT        NOT NULL,
            committee_id         UUID,
            committee_seal_id    UUID,
            decision_at          TIMESTAMPTZ NOT NULL,
            zone                 TEXT        NOT NULL,
            currency             TEXT        NOT NULL DEFAULT 'XOF',

            item_id              TEXT,
            alias_raw            TEXT        NOT NULL,

            quantity             NUMERIC,
            unit                 TEXT,
            price_paid           NUMERIC,

            supplier_id          TEXT,
            supplier_name_raw    TEXT        NOT NULL,

            source_hashes        JSONB       NOT NULL DEFAULT '{}',
            scoring_meta         JSONB       NOT NULL DEFAULT '{}',

            snapshot_hash        TEXT        NOT NULL,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT uq_snapshot_idempotence UNIQUE (case_id, snapshot_hash)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_decision_snapshots_case_id
        ON public.decision_snapshots(case_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_decision_snapshots_committee_id
        ON public.decision_snapshots(committee_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_decision_snapshots_decision_at
        ON public.decision_snapshots(decision_at)
    """)

    # ---------------------------------------- trigger append-only decision_snapshots
    op.execute("""
        CREATE OR REPLACE FUNCTION public.enforce_decision_snapshots_append_only()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'append-only violation: decision_snapshots immutable (op=% id=%)',
                TG_OP, OLD.snapshot_id;
        END;
        $$
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_decision_snapshots_append_only'
                  AND tgrelid = 'public.decision_snapshots'::regclass
            ) THEN
                CREATE TRIGGER trg_decision_snapshots_append_only
                BEFORE UPDATE OR DELETE ON public.decision_snapshots
                FOR EACH ROW EXECUTE FUNCTION public.enforce_decision_snapshots_append_only();
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_decision_snapshots_append_only'
                  AND tgrelid = 'public.decision_snapshots'::regclass
            ) THEN
                DROP TRIGGER trg_decision_snapshots_append_only ON public.decision_snapshots;
            END IF;
        END $$
    """)
    op.execute("DROP FUNCTION IF EXISTS public.enforce_decision_snapshots_append_only()")
    op.execute("DROP TABLE IF EXISTS public.decision_snapshots")
