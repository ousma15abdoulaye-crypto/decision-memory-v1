"""028 -- committee core tables: committees, committee_members, committee_decisions,
committee_events (append-only) -- M-COMMITTEE-CORE ADR-0008/ADR-0011."""

from alembic import op

revision = "028_create_committee_tables"
down_revision = "027_add_cases_currency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ committees
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.committees (
            committee_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id            TEXT        NOT NULL,
            org_id             TEXT        NOT NULL,
            committee_type     TEXT        NOT NULL DEFAULT 'achat'
                               CHECK (committee_type IN ('achat','technique','mixte')),
            status             TEXT        NOT NULL DEFAULT 'draft'
                               CHECK (status IN ('draft','open','in_review','sealed','cancelled')),
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by         TEXT        NOT NULL,
            cancelled_reason   TEXT,
            sealed_at          TIMESTAMPTZ,
            sealed_by          TEXT
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_committees_case_id
        ON public.committees(case_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_committees_status
        ON public.committees(status)
    """)

    # --------------------------------------------------------- committee_members
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.committee_members (
            member_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            committee_id       UUID        NOT NULL
                               REFERENCES public.committees(committee_id) ON DELETE RESTRICT,
            user_ref           TEXT        NOT NULL,
            role               TEXT        NOT NULL
                               CHECK (role IN ('chair','member','secretary','observer','approver')),
            can_vote           BOOLEAN     NOT NULL DEFAULT false,
            can_seal           BOOLEAN     NOT NULL DEFAULT false,
            can_edit_minutes   BOOLEAN     NOT NULL DEFAULT false,
            is_mandatory       BOOLEAN     NOT NULL DEFAULT false,
            quorum_counted     BOOLEAN     NOT NULL DEFAULT false,
            status             TEXT        NOT NULL DEFAULT 'invited'
                               CHECK (status IN ('invited','active','recused','absent','signed')),
            joined_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_committee_members_committee_id
        ON public.committee_members(committee_id)
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_committee_members_unique_user
        ON public.committee_members(committee_id, user_ref)
        WHERE status <> 'recused'
    """)

    # ------------------------------------------------------- committee_decisions
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.committee_decisions (
            decision_id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            committee_id           UUID        NOT NULL
                                   REFERENCES public.committees(committee_id) ON DELETE RESTRICT,
            case_id                TEXT        NOT NULL,
            selected_supplier_id   TEXT,
            supplier_name_raw      TEXT,
            decision_status        TEXT        NOT NULL DEFAULT 'proposed'
                                   CHECK (decision_status IN
                                   ('proposed','validated','sealed','rejected','no_award')),
            rationale              TEXT        NOT NULL,
            decision_at            TIMESTAMPTZ,
            sealed_by              TEXT,
            seal_id                UUID UNIQUE,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_supplier_or_no_award CHECK (
                selected_supplier_id IS NOT NULL
                OR decision_status IN ('no_award', 'sealed', 'rejected')
            )
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_committee_decisions_committee_id
        ON public.committee_decisions(committee_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_committee_decisions_case_id
        ON public.committee_decisions(case_id)
    """)

    # --------------------------------------------------------- committee_events (append-only)
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.committee_events (
            event_id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            committee_id       UUID        NOT NULL
                               REFERENCES public.committees(committee_id) ON DELETE RESTRICT,
            event_type         TEXT        NOT NULL
                               CHECK (event_type IN (
                                   'committee_created',
                                   'member_added',
                                   'member_removed',
                                   'meeting_opened',
                                   'vote_recorded',
                                   'recommendation_set',
                                   'seal_requested',
                                   'seal_completed',
                                   'seal_rejected',
                                   'snapshot_emitted',
                                   'committee_cancelled'
                               )),
            payload            JSONB       NOT NULL DEFAULT '{}',
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by         TEXT        NOT NULL
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_committee_events_committee_id
        ON public.committee_events(committee_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_committee_events_type
        ON public.committee_events(event_type)
    """)

    # ---------------------------------------- trigger append-only committee_events
    op.execute("""
        CREATE OR REPLACE FUNCTION public.enforce_committee_events_append_only()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'append-only violation: committee_events immutable (op=% id=%)',
                TG_OP, OLD.event_id;
        END;
        $$
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_committee_events_append_only'
                  AND tgrelid = 'public.committee_events'::regclass
            ) THEN
                CREATE TRIGGER trg_committee_events_append_only
                BEFORE UPDATE OR DELETE ON public.committee_events
                FOR EACH ROW EXECUTE FUNCTION public.enforce_committee_events_append_only();
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_committee_events_append_only'
                  AND tgrelid = 'public.committee_events'::regclass
            ) THEN
                DROP TRIGGER trg_committee_events_append_only ON public.committee_events;
            END IF;
        END $$
    """)
    op.execute("DROP FUNCTION IF EXISTS public.enforce_committee_events_append_only()")
    op.execute("DROP TABLE IF EXISTS public.committee_events")
    op.execute("DROP TABLE IF EXISTS public.committee_decisions")
    op.execute("DROP TABLE IF EXISTS public.committee_members")
    op.execute("DROP TABLE IF EXISTS public.committees")
