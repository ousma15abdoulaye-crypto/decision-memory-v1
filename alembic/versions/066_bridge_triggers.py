"""066 — VIVANT V2 C-1: bridge triggers source tables → dms_event_index (GAP-1).

Creates 11 AFTER INSERT FOR EACH ROW triggers on source tables that
feed the central event index (migration 061).  Also adds:
  - A DEFAULT partition so inserts outside the 2025-H2 window never fail.

Source tables:
  public.m12_correction_log      → annotation domain
  public.m13_correction_log      → procurement domain
  public.decision_snapshots      → decision domain
  public.market_signals_v2       → market domain
  public.decision_history        → decision domain
  public.score_history           → procurement domain
  public.elimination_log         → procurement domain
  public.pipeline_runs           → pipeline domain
  public.pipeline_step_runs      → pipeline domain
  couche_a.agent_runs_log        → agent domain
  public.submission_registry_events → procurement domain (conditional)

UUID PKs are hashed via hashtext()::bigint.
BIGSERIAL PKs are used directly.
Summaries are minimal (S5: never full payload).

Revision ID: 066_bridge_triggers
Revises    : 065_llm_traces
"""

from alembic import op

revision = "066_bridge_triggers"
down_revision = "065_llm_traces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 0. DEFAULT partition (GAP-7 folded here) ─────────────────────
    op.execute("""
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_inherits i
            JOIN pg_class p ON p.oid = i.inhparent
            JOIN pg_class c ON c.oid = i.inhrelid
            JOIN pg_namespace pn ON pn.oid = p.relnamespace
            WHERE pn.nspname = 'public'
              AND p.relname  = 'dms_event_index'
              AND c.relname  = 'dms_event_index_default'
        ) THEN
            CREATE TABLE public.dms_event_index_default
                PARTITION OF public.dms_event_index DEFAULT;
        END IF;
    END $$;
    """)

    # ── 1. m12_correction_log ─────────────────────────────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION public.fn_bridge_m12_correction_to_event_index()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        INSERT INTO public.dms_event_index (
            event_domain, source_table, source_pk,
            case_id, document_id,
            aggregate_type, event_type, event_time, summary, schema_version
        ) VALUES (
            'annotation',
            'm12_correction_log',
            NEW.id,
            NULL,
            NEW.document_id,
            'm12_correction_log',
            'm12.correction.created',
            COALESCE(NEW.created_at, NOW()),
            json_build_object(
                'correction_type', NEW.correction_type,
                'field_corrected',  NEW.field_corrected
            )::jsonb,
            '1.0'
        );
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_bridge_m12_correction ON public.m12_correction_log;
    CREATE TRIGGER trg_bridge_m12_correction
        AFTER INSERT ON public.m12_correction_log
        FOR EACH ROW EXECUTE FUNCTION public.fn_bridge_m12_correction_to_event_index();
    """)

    # ── 2. m13_correction_log ─────────────────────────────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION public.fn_bridge_m13_correction_to_event_index()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        INSERT INTO public.dms_event_index (
            event_domain, source_table, source_pk,
            case_id,
            aggregate_type, event_type, event_time, summary, schema_version
        ) VALUES (
            'procurement',
            'm13_correction_log',
            NEW.id,
            NEW.case_id,
            'm13_correction_log',
            'm13.correction.created',
            COALESCE(NEW.created_at, NOW()),
            json_build_object(
                'field_path',        NEW.field_path,
                'correction_source', NEW.correction_source
            )::jsonb,
            '1.0'
        );
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_bridge_m13_correction ON public.m13_correction_log;
    CREATE TRIGGER trg_bridge_m13_correction
        AFTER INSERT ON public.m13_correction_log
        FOR EACH ROW EXECUTE FUNCTION public.fn_bridge_m13_correction_to_event_index();
    """)

    # ── 3. decision_snapshots ─────────────────────────────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION public.fn_bridge_decision_snapshot_to_event_index()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        INSERT INTO public.dms_event_index (
            event_domain, source_table, source_pk,
            case_id, supplier_id, item_id,
            aggregate_type, event_type, event_time, summary, schema_version
        ) VALUES (
            'decision',
            'decision_snapshots',
            hashtext(NEW.snapshot_id::text)::bigint,
            NEW.case_id,
            NEW.supplier_id,
            NEW.item_id,
            'decision_snapshots',
            'decision.snapshot.created',
            COALESCE(NEW.created_at, NOW()),
            json_build_object(
                'zone',           NEW.zone,
                'decision_at',    NEW.decision_at
            )::jsonb,
            '1.0'
        );
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_bridge_decision_snapshot ON public.decision_snapshots;
    CREATE TRIGGER trg_bridge_decision_snapshot
        AFTER INSERT ON public.decision_snapshots
        FOR EACH ROW EXECUTE FUNCTION public.fn_bridge_decision_snapshot_to_event_index();
    """)

    # ── 4. market_signals_v2 ──────────────────────────────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION public.fn_bridge_market_signal_to_event_index()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        INSERT INTO public.dms_event_index (
            event_domain, source_table, source_pk,
            item_id,
            aggregate_type, event_type, event_time, summary, schema_version
        ) VALUES (
            'market',
            'market_signals_v2',
            hashtext(NEW.id::text)::bigint,
            NEW.item_id,
            'market_signals_v2',
            'market.signal.created',
            COALESCE(NEW.computed_at, NOW()),
            json_build_object(
                'zone_id',     NEW.zone_id,
                'alert_level', NEW.alert_level,
                'signal_quality', NEW.signal_quality
            )::jsonb,
            '1.0'
        );
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_bridge_market_signal ON public.market_signals_v2;
    CREATE TRIGGER trg_bridge_market_signal
        AFTER INSERT ON public.market_signals_v2
        FOR EACH ROW EXECUTE FUNCTION public.fn_bridge_market_signal_to_event_index();
    """)

    # ── 5. decision_history ───────────────────────────────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION public.fn_bridge_decision_history_to_event_index()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        INSERT INTO public.dms_event_index (
            event_domain, source_table, source_pk,
            item_id,
            aggregate_type, event_type, event_time, summary, schema_version
        ) VALUES (
            'decision',
            'decision_history',
            hashtext(NEW.id::text)::bigint,
            NEW.item_id,
            'decision_history',
            'decision.history.recorded',
            COALESCE(NEW.created_at, NOW()),
            json_build_object(
                'zone_id',       NEW.zone_id,
                'decision_type', NEW.decision_type,
                'decided_at',    NEW.decided_at
            )::jsonb,
            '1.0'
        );
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_bridge_decision_history ON public.decision_history;
    CREATE TRIGGER trg_bridge_decision_history
        AFTER INSERT ON public.decision_history
        FOR EACH ROW EXECUTE FUNCTION public.fn_bridge_decision_history_to_event_index();
    """)

    # ── 6. score_history ─────────────────────────────────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION public.fn_bridge_score_history_to_event_index()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        INSERT INTO public.dms_event_index (
            event_domain, source_table, source_pk,
            case_id,
            aggregate_type, event_type, event_time, summary, schema_version
        ) VALUES (
            'procurement',
            'score_history',
            hashtext(NEW.id::text)::bigint,
            NEW.case_id,
            'score_history',
            'm14.score.recorded',
            COALESCE(NEW.created_at, NOW()),
            json_build_object(
                'criterion_key', NEW.criterion_key,
                'scored_by',     NEW.scored_by
            )::jsonb,
            '1.0'
        );
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_bridge_score_history ON public.score_history;
    CREATE TRIGGER trg_bridge_score_history
        AFTER INSERT ON public.score_history
        FOR EACH ROW EXECUTE FUNCTION public.fn_bridge_score_history_to_event_index();
    """)

    # ── 7. elimination_log ───────────────────────────────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION public.fn_bridge_elimination_log_to_event_index()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        INSERT INTO public.dms_event_index (
            event_domain, source_table, source_pk,
            case_id,
            aggregate_type, event_type, event_time, summary, schema_version
        ) VALUES (
            'procurement',
            'elimination_log',
            hashtext(NEW.id::text)::bigint,
            NEW.case_id,
            'elimination_log',
            'm14.elimination.recorded',
            COALESCE(NEW.created_at, NOW()),
            json_build_object(
                'check_id',   NEW.check_id,
                'check_name', NEW.check_name
            )::jsonb,
            '1.0'
        );
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_bridge_elimination_log ON public.elimination_log;
    CREATE TRIGGER trg_bridge_elimination_log
        AFTER INSERT ON public.elimination_log
        FOR EACH ROW EXECUTE FUNCTION public.fn_bridge_elimination_log_to_event_index();
    """)

    # ── 8. pipeline_runs ─────────────────────────────────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION public.fn_bridge_pipeline_run_to_event_index()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        INSERT INTO public.dms_event_index (
            event_domain, source_table, source_pk,
            case_id,
            aggregate_type, event_type, event_time, summary, schema_version
        ) VALUES (
            'pipeline',
            'pipeline_runs',
            hashtext(NEW.pipeline_run_id::text)::bigint,
            NEW.case_id,
            'pipeline_runs',
            'pipeline.run.created',
            COALESCE(NEW.started_at, NOW()),
            json_build_object(
                'pipeline_type', NEW.pipeline_type,
                'mode',          NEW.mode,
                'status',        NEW.status
            )::jsonb,
            '1.0'
        );
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_bridge_pipeline_run ON public.pipeline_runs;
    CREATE TRIGGER trg_bridge_pipeline_run
        AFTER INSERT ON public.pipeline_runs
        FOR EACH ROW EXECUTE FUNCTION public.fn_bridge_pipeline_run_to_event_index();
    """)

    # ── 9. pipeline_step_runs ─────────────────────────────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION public.fn_bridge_pipeline_step_to_event_index()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    DECLARE
        v_case_id TEXT;
    BEGIN
        SELECT case_id INTO v_case_id
        FROM public.pipeline_runs
        WHERE pipeline_run_id = NEW.pipeline_run_id;

        INSERT INTO public.dms_event_index (
            event_domain, source_table, source_pk,
            case_id,
            aggregate_type, event_type, event_time, summary, schema_version
        ) VALUES (
            'pipeline',
            'pipeline_step_runs',
            hashtext(NEW.step_run_id::text)::bigint,
            v_case_id,
            'pipeline_step_runs',
            'pipeline.step.created',
            COALESCE(NEW.started_at, NOW()),
            json_build_object(
                'step_name', NEW.step_name,
                'status',    NEW.status
            )::jsonb,
            '1.0'
        );
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_bridge_pipeline_step ON public.pipeline_step_runs;
    CREATE TRIGGER trg_bridge_pipeline_step
        AFTER INSERT ON public.pipeline_step_runs
        FOR EACH ROW EXECUTE FUNCTION public.fn_bridge_pipeline_step_to_event_index();
    """)

    # ── 10. couche_a.agent_runs_log ───────────────────────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION couche_a.fn_bridge_agent_run_to_event_index()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        INSERT INTO public.dms_event_index (
            event_domain, source_table, source_pk,
            aggregate_type, event_type, event_time, summary, schema_version
        ) VALUES (
            'agent',
            'couche_a.agent_runs_log',
            hashtext(NEW.run_id::text)::bigint,
            'agent_runs_log',
            'agent.run.created',
            COALESCE(NEW.started_at, NOW()),
            json_build_object(
                'agent_type', NEW.agent_type,
                'status',     NEW.status
            )::jsonb,
            '1.0'
        );
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_bridge_agent_run ON couche_a.agent_runs_log;
    CREATE TRIGGER trg_bridge_agent_run
        AFTER INSERT ON couche_a.agent_runs_log
        FOR EACH ROW EXECUTE FUNCTION couche_a.fn_bridge_agent_run_to_event_index();
    """)

    # ── 11. submission_registry_events (conditional — table may not exist) ──
    op.execute("""
    DO $$ BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name   = 'submission_registry_events'
        ) THEN
            CREATE OR REPLACE FUNCTION
                public.fn_bridge_submission_event_to_event_index()
            RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
            BEGIN
                INSERT INTO public.dms_event_index (
                    event_domain, source_table, source_pk,
                    case_id,
                    aggregate_type, event_type, event_time, summary, schema_version
                ) VALUES (
                    'procurement',
                    'submission_registry_events',
                    hashtext(NEW.id::text)::bigint,
                    NEW.case_id,
                    'submission_registry_events',
                    'submission.event.created',
                    COALESCE(NEW.created_at, NOW()),
                    json_build_object('event_type', NEW.event_type)::jsonb,
                    '1.0'
                );
                RETURN NEW;
            END;
            $fn$;

            DROP TRIGGER IF EXISTS trg_bridge_submission_event
                ON public.submission_registry_events;
            CREATE TRIGGER trg_bridge_submission_event
                AFTER INSERT ON public.submission_registry_events
                FOR EACH ROW
                EXECUTE FUNCTION
                    public.fn_bridge_submission_event_to_event_index();
        END IF;
    END $$;
    """)


def downgrade() -> None:
    # Remove submission_registry_events trigger (conditional)
    op.execute("""
    DO $$ BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name   = 'submission_registry_events'
        ) THEN
            DROP TRIGGER IF EXISTS trg_bridge_submission_event
                ON public.submission_registry_events;
            DROP FUNCTION IF EXISTS
                public.fn_bridge_submission_event_to_event_index();
        END IF;
    END $$;
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS trg_bridge_agent_run ON couche_a.agent_runs_log;
    DROP FUNCTION IF EXISTS couche_a.fn_bridge_agent_run_to_event_index();

    DROP TRIGGER IF EXISTS trg_bridge_pipeline_step ON public.pipeline_step_runs;
    DROP FUNCTION IF EXISTS public.fn_bridge_pipeline_step_to_event_index();

    DROP TRIGGER IF EXISTS trg_bridge_pipeline_run ON public.pipeline_runs;
    DROP FUNCTION IF EXISTS public.fn_bridge_pipeline_run_to_event_index();

    DROP TRIGGER IF EXISTS trg_bridge_elimination_log ON public.elimination_log;
    DROP FUNCTION IF EXISTS public.fn_bridge_elimination_log_to_event_index();

    DROP TRIGGER IF EXISTS trg_bridge_score_history ON public.score_history;
    DROP FUNCTION IF EXISTS public.fn_bridge_score_history_to_event_index();

    DROP TRIGGER IF EXISTS trg_bridge_decision_history ON public.decision_history;
    DROP FUNCTION IF EXISTS public.fn_bridge_decision_history_to_event_index();

    DROP TRIGGER IF EXISTS trg_bridge_market_signal ON public.market_signals_v2;
    DROP FUNCTION IF EXISTS public.fn_bridge_market_signal_to_event_index();

    DROP TRIGGER IF EXISTS trg_bridge_decision_snapshot ON public.decision_snapshots;
    DROP FUNCTION IF EXISTS public.fn_bridge_decision_snapshot_to_event_index();

    DROP TRIGGER IF EXISTS trg_bridge_m13_correction ON public.m13_correction_log;
    DROP FUNCTION IF EXISTS public.fn_bridge_m13_correction_to_event_index();

    DROP TRIGGER IF EXISTS trg_bridge_m12_correction ON public.m12_correction_log;
    DROP FUNCTION IF EXISTS public.fn_bridge_m12_correction_to_event_index();

    DROP TABLE IF EXISTS public.dms_event_index_default;
    """)
