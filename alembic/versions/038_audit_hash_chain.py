"""M1B — Audit Hash Chain.

Crée : audit_log · séquence chain_seq · index · triggers append-only ·
        fn_reject_audit_mutation · fn_verify_audit_chain.

SQL brut uniquement (RÈGLE-12).
Idempotent : IF NOT EXISTS partout.
Ne touche pas : users · token_blacklist · tables métier.

Revision ID: 038_audit_hash_chain
Revises    : 037_security_baseline
"""

from alembic import op

revision = "038_audit_hash_chain"
down_revision = "037_security_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extension pgcrypto ────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # ── 2. Séquence explicite pour chain_seq ─────────────────────────────────
    op.execute("""
        CREATE SEQUENCE IF NOT EXISTS audit_log_chain_seq_seq
            START WITH 1
            INCREMENT BY 1
            NO CYCLE;
    """)

    # ── 3. Table audit_log ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            chain_seq         BIGINT      NOT NULL UNIQUE
                                          DEFAULT nextval('audit_log_chain_seq_seq'),
            entity            TEXT        NOT NULL,
            entity_id         TEXT        NOT NULL,
            action            TEXT        NOT NULL,
            actor_id          TEXT,
            payload           JSONB,
            payload_canonical TEXT        NOT NULL DEFAULT '',
            ip_address        INET,
            timestamp         TIMESTAMPTZ NOT NULL DEFAULT now(),
            prev_hash         TEXT        NOT NULL,
            event_hash        TEXT        NOT NULL
        );
    """)

    # ── 4. Index ─────────────────────────────────────────────────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_entity
            ON audit_log(entity, entity_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_actor
            ON audit_log(actor_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp
            ON audit_log(timestamp DESC);
    """)

    # ── 5. Fonction trigger append-only ──────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_reject_audit_mutation()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'audit_log est append-only — % non autorisé et détectable (protection applicative)',
                TG_OP;
            RETURN NULL;
        END;
        $$;
    """)

    # ── 6. Trigger DELETE + UPDATE (FOR EACH ROW) ────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_audit_log_no_delete_update'
            ) THEN
                CREATE TRIGGER trg_audit_log_no_delete_update
                BEFORE DELETE OR UPDATE ON audit_log
                FOR EACH ROW EXECUTE FUNCTION fn_reject_audit_mutation();
            END IF;
        END;
        $$;
    """)

    # ── 7. Trigger TRUNCATE (FOR EACH STATEMENT) — CORR-04 ──────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_audit_log_no_truncate'
            ) THEN
                CREATE TRIGGER trg_audit_log_no_truncate
                BEFORE TRUNCATE ON audit_log
                FOR EACH STATEMENT EXECUTE FUNCTION fn_reject_audit_mutation();
            END IF;
        END;
        $$;
    """)

    # ── 8. Fonction vérification chaîne ──────────────────────────────────────
    # Utilise to_char(... AT TIME ZONE 'UTC', ...) pour correspondre exactement
    # au format Python : timestamp_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{microsecond:06d}Z"
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_verify_audit_chain(
            p_from BIGINT DEFAULT 0,
            p_to   BIGINT DEFAULT 9223372036854775807
        )
        RETURNS BOOLEAN LANGUAGE plpgsql AS $$
        DECLARE
            rec      RECORD;
            prev     TEXT := 'GENESIS';
            computed TEXT;
        BEGIN
            FOR rec IN
                SELECT *
                FROM audit_log
                WHERE chain_seq BETWEEN p_from AND p_to
                ORDER BY chain_seq ASC
            LOOP
                computed := encode(
                    digest(
                        rec.entity                                              ||
                        rec.entity_id                                           ||
                        rec.action                                              ||
                        COALESCE(rec.actor_id, '')                              ||
                        rec.payload_canonical                                   ||
                        to_char(rec.timestamp AT TIME ZONE 'UTC',
                                'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')               ||
                        rec.chain_seq::text                                     ||
                        prev,
                        'sha256'
                    ),
                    'hex'
                );

                IF computed <> rec.event_hash THEN
                    RETURN FALSE;
                END IF;

                IF rec.prev_hash <> prev THEN
                    RETURN FALSE;
                END IF;

                prev := rec.event_hash;
            END LOOP;

            RETURN TRUE;
        END;
        $$;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS fn_verify_audit_chain(BIGINT, BIGINT);")
    op.execute("DROP FUNCTION IF EXISTS fn_reject_audit_mutation() CASCADE;")
    op.execute("DROP TABLE IF EXISTS audit_log;")
    op.execute("DROP SEQUENCE IF EXISTS audit_log_chain_seq_seq;")
