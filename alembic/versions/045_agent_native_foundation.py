"""
045 · Agent-Native Foundation (ADR-010)

CLASSIFICATION : COUCHE A — Infrastructure Agents

  couche_a.agent_checkpoints   → Mémoire de session (GAP-2)
  couche_a.agent_runs_log      → Observabilité et FinOps (GAP-3)
                                  APPEND-ONLY — ADR-010
  couche_a.fn_dms_event_notify → Bus pg_notify (GAP-1)

CONVENTION SQL : op.execute() UNIQUEMENT — zéro helper Alembic
TRIGGERS NOTIFY : FOR EACH STATEMENT + RETURN NULL obligatoire

Schéma couche_a : créé par 045 (premier propriétaire).
  public = couche_a métier (lots, market_signals_v2, etc.)
  couche_b = procurement dict (021)
  couche_a = infrastructure agents UNIQUEMENT (045)

Revision  : 045_agent_native_foundation
Down      : 044_decision_history
"""

from alembic import op

revision = "045_agent_native_foundation"
down_revision = "044_decision_history"
branch_labels = None
depends_on = None


# ════════════════════════════════════════════════════════════════
# UPGRADE
# ════════════════════════════════════════════════════════════════

def upgrade() -> None:

    # ── 0. SCHÉMA couche_a ─────────────────────────────────────────
    # Premier créateur de couche_a dans ce projet.
    # Propriétaire : migration 045.
    op.execute("CREATE SCHEMA IF NOT EXISTS couche_a;")

    # ── 1. MÉMOIRE AGENT — couche_a.agent_checkpoints (GAP-2) ──────
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_a.agent_checkpoints (
            checkpoint_id  UUID          PRIMARY KEY
                           DEFAULT gen_random_uuid(),
            thread_id      TEXT          NOT NULL,
            agent_type     TEXT          NOT NULL
                           CHECK (agent_type IN (
                               'market_signal',
                               'supplier_eval',
                               'query',
                               'classify',
                               'compliance'
                           )),
            step_name      TEXT          NOT NULL,
            state_json     JSONB         NOT NULL,
            token_count    INTEGER       DEFAULT 0,
            created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            expires_at     TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS idx_agent_ckpt_thread
            ON couche_a.agent_checkpoints(thread_id, created_at DESC);
    """)

    # ── 2. OBSERVABILITÉ / FINOPS — couche_a.agent_runs_log (GAP-3)
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_a.agent_runs_log (
            run_id        UUID            PRIMARY KEY
                          DEFAULT gen_random_uuid(),
            agent_type    TEXT            NOT NULL,
            trigger_event TEXT,
            items_in      INTEGER         DEFAULT 0,
            items_ok      INTEGER         DEFAULT 0,
            items_flagged INTEGER         DEFAULT 0,
            items_error   INTEGER         DEFAULT 0,
            cost_usd      NUMERIC(10,5)   DEFAULT 0.00000,
            model_used    TEXT,
            duration_ms   INTEGER,
            status        TEXT            NOT NULL DEFAULT 'running'
                          CHECK (status IN (
                              'running', 'done', 'failed', 'partial'
                          )),
            error_detail  TEXT,
            started_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            ended_at      TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS idx_agent_runs_type
            ON couche_a.agent_runs_log(agent_type, started_at DESC);
    """)

    # ── 3. GARDE APPEND-ONLY sur agent_runs_log ─────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION couche_a.fn_prevent_runs_delete()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'ADR-010 : agent_runs_log est APPEND-ONLY. '
                'Suppression interdite. run_id=%', OLD.run_id;
            RETURN NULL;
        END;
        $$;

        DROP TRIGGER IF EXISTS trg_agent_runs_no_delete ON couche_a.agent_runs_log;
        CREATE TRIGGER trg_agent_runs_no_delete
        BEFORE DELETE ON couche_a.agent_runs_log
        FOR EACH ROW
        EXECUTE FUNCTION couche_a.fn_prevent_runs_delete();
    """)

    # ── 4. BUS D'ÉVÉNEMENTS — fn_dms_event_notify (GAP-1) ───────────
    op.execute("""
        CREATE OR REPLACE FUNCTION couche_a.fn_dms_event_notify()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        DECLARE
            payload TEXT;
        BEGIN
            payload := json_build_object(
                'table', TG_TABLE_NAME,
                'op',    TG_OP,
                'ts',    extract(epoch from now())
            )::text;
            PERFORM pg_notify('dms_events', payload);
            RETURN NULL;
        END;
        $$;
    """)

    # ── 5. ATTACHEMENT TRIGGERS NOTIFY ──────────────────────────────
    op.execute("""
        DROP TRIGGER IF EXISTS trg_notify_market_signals ON public.market_signals_v2;
        CREATE TRIGGER trg_notify_market_signals
        AFTER INSERT ON public.market_signals_v2
        FOR EACH STATEMENT
        EXECUTE FUNCTION couche_a.fn_dms_event_notify();
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_notify_market_surveys ON public.market_surveys;
        CREATE TRIGGER trg_notify_market_surveys
        AFTER INSERT ON public.market_surveys
        FOR EACH STATEMENT
        EXECUTE FUNCTION couche_a.fn_dms_event_notify();
    """)

    # ── 6. VÉRIFICATION POST-UPGRADE (FAIL-LOUD) ────────────────────
    op.execute("""
        DO $$
        DECLARE v INTEGER;
        BEGIN
            SELECT COUNT(*) INTO v
            FROM information_schema.tables
            WHERE table_schema = 'couche_a'
            AND   table_name   = 'agent_runs_log';
            IF v = 0 THEN
                RAISE EXCEPTION
                    '045 UPGRADE ÉCHOUÉ — couche_a.agent_runs_log absente';
            END IF;

            SELECT COUNT(*) INTO v
            FROM information_schema.tables
            WHERE table_schema = 'couche_a'
            AND   table_name   = 'agent_checkpoints';
            IF v = 0 THEN
                RAISE EXCEPTION
                    '045 UPGRADE ÉCHOUÉ — couche_a.agent_checkpoints absente';
            END IF;

            SELECT COUNT(*) INTO v
            FROM information_schema.triggers
            WHERE trigger_name = 'trg_notify_market_signals';
            IF v = 0 THEN
                RAISE EXCEPTION
                    '045 UPGRADE ÉCHOUÉ — trg_notify_market_signals absent';
            END IF;

            SELECT COUNT(*) INTO v
            FROM information_schema.triggers
            WHERE trigger_name = 'trg_notify_market_surveys';
            IF v = 0 THEN
                RAISE EXCEPTION
                    '045 UPGRADE ÉCHOUÉ — trg_notify_market_surveys absent';
            END IF;

            RAISE NOTICE
                '045 OK — Agent-Native Foundation opérationnelle';
        END;
        $$;
    """)


# ════════════════════════════════════════════════════════════════
# DOWNGRADE
# Séquence STRICTE : triggers → fonctions → tables → schéma (si vide)
# ════════════════════════════════════════════════════════════════

def downgrade() -> None:

    # 1. Triggers notify (sur tables public.*)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_notify_market_surveys
        ON public.market_surveys;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_notify_market_signals
        ON public.market_signals_v2;
    """)

    # 2. Trigger append-only (sur couche_a.agent_runs_log)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_agent_runs_no_delete
        ON couche_a.agent_runs_log;
    """)

    # 3. Fonctions
    op.execute("""
        DROP FUNCTION IF EXISTS couche_a.fn_dms_event_notify() CASCADE;
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS couche_a.fn_prevent_runs_delete() CASCADE;
    """)

    # 4. Tables
    op.execute("""
        DROP TABLE IF EXISTS couche_a.agent_runs_log CASCADE;
    """)
    op.execute("""
        DROP TABLE IF EXISTS couche_a.agent_checkpoints CASCADE;
    """)

    # 5. Schéma — seulement si vide de tables non-045
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'couche_a'
                AND   table_name NOT IN (
                    'agent_checkpoints',
                    'agent_runs_log'
                )
            ) THEN
                DROP SCHEMA IF EXISTS couche_a;
            END IF;
        END;
        $$;
    """)
