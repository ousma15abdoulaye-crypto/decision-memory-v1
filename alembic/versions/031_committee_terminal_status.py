"""031 -- enforce_committee_terminal_status: sealed est terminal (PATCH-5).

Interdit toute transition depuis committees.status='sealed' vers un autre statut.
"""

from alembic import op

revision = "031_committee_terminal_status"
down_revision = "030_committee_lock_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.enforce_committee_terminal_status()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF OLD.status = 'sealed' AND NEW.status IS DISTINCT FROM OLD.status THEN
                    RAISE EXCEPTION
                        'terminal-status violation: committee % already sealed (% -> %)',
                        OLD.committee_id, OLD.status, NEW.status;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_committees_terminal_status_lock'
                  AND tgrelid = 'public.committees'::regclass
            ) THEN
                CREATE TRIGGER trg_committees_terminal_status_lock
                BEFORE UPDATE ON public.committees
                FOR EACH ROW EXECUTE FUNCTION public.enforce_committee_terminal_status();
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_committees_terminal_status_lock'
                  AND tgrelid = 'public.committees'::regclass
            ) THEN
                DROP TRIGGER trg_committees_terminal_status_lock ON public.committees;
            END IF;
        END $$
    """)
    op.execute("DROP FUNCTION IF EXISTS public.enforce_committee_terminal_status()")
