"""077 - Fix bridge trigger functions after 074 dropped case_id from score_history/elimination_log

Revision ID: 077_fix_bridge_triggers_workspace_id
Revises: 076_evaluation_documents_workspace_unique
Create Date: 2026-04-04

Migration 074 dropped case_id CASCADE from score_history and elimination_log.
The bridge trigger functions fn_bridge_score_history_to_event_index() and
fn_bridge_elimination_log_to_event_index() (created in 066) still reference
NEW.case_id, causing UndefinedColumn on every INSERT into those tables.

Fix: replace NEW.case_id with NULL in the dms_event_index INSERT.
The case_id column in dms_event_index is nullable; NULL is the correct value
when the source row carries workspace_id instead.

REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "077_fix_bridge_triggers_workspace_id"
down_revision = "076_evaluation_documents_workspace_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
            NULL,
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
    """)

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
            NULL,
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
    """)


def downgrade() -> None:
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
    """)

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
    """)
