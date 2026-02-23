"""030 -- enforce_committee_lock: verrou post-seal intelligent (PATCH-1).

Bloque INSERT/UPDATE sur committee_members et committee_decisions après seal.
Exception unique : UPDATE de sealing sur committee_decisions (transition atomique).
"""

from alembic import op

revision = "030_committee_lock_trigger"
down_revision = "029_create_decision_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----------------------------------------- fonction verrou intelligent
    op.execute("""
        CREATE OR REPLACE FUNCTION public.enforce_committee_lock()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        DECLARE
            v_committee_id UUID;
            v_status TEXT;
            is_seal_transition BOOLEAN := FALSE;
        BEGIN
            v_committee_id := COALESCE(NEW.committee_id, OLD.committee_id);

            SELECT status INTO v_status
            FROM public.committees
            WHERE committee_id = v_committee_id
            FOR SHARE;

            -- Pas encore scellé → laisser passer
            IF v_status IS DISTINCT FROM 'sealed' THEN
                RETURN NEW;
            END IF;

            -- Comité scellé → blocage par défaut.
            -- Exception unique : UPDATE de sealing sur committee_decisions.
            IF TG_TABLE_NAME = 'committee_decisions' AND TG_OP = 'UPDATE' THEN
                is_seal_transition :=
                    (OLD.decision_status IS DISTINCT FROM 'sealed')
                    AND (NEW.decision_status = 'sealed')
                    AND (NEW.seal_id IS NOT NULL)
                    AND (NEW.decision_at IS NOT NULL)
                    AND (NEW.sealed_by IS NOT NULL);

                IF is_seal_transition THEN
                    RETURN NEW;
                END IF;
            END IF;

            RAISE EXCEPTION
                'committee_lock violation: committee % is sealed (table=% op=%)',
                v_committee_id, TG_TABLE_NAME, TG_OP;
        END;
        $$
    """)

    # ----------------------------------------- trigger committee_members
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_committee_members_lock'
                  AND tgrelid = 'public.committee_members'::regclass
            ) THEN
                CREATE TRIGGER trg_committee_members_lock
                BEFORE INSERT OR UPDATE ON public.committee_members
                FOR EACH ROW EXECUTE FUNCTION public.enforce_committee_lock();
            END IF;
        END $$
    """)

    # ----------------------------------------- trigger committee_decisions
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_committee_decisions_lock'
                  AND tgrelid = 'public.committee_decisions'::regclass
            ) THEN
                CREATE TRIGGER trg_committee_decisions_lock
                BEFORE INSERT OR UPDATE ON public.committee_decisions
                FOR EACH ROW EXECUTE FUNCTION public.enforce_committee_lock();
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_committee_decisions_lock'
                  AND tgrelid = 'public.committee_decisions'::regclass
            ) THEN
                DROP TRIGGER trg_committee_decisions_lock ON public.committee_decisions;
            END IF;
        END $$
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_committee_members_lock'
                  AND tgrelid = 'public.committee_members'::regclass
            ) THEN
                DROP TRIGGER trg_committee_members_lock ON public.committee_members;
            END IF;
        END $$
    """)
    op.execute("DROP FUNCTION IF EXISTS public.enforce_committee_lock()")
