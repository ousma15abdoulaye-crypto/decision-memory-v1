"""
alembic/versions/m7_3_dict_nerve_center.py

M7.3 Dict Nerve Center · Alignement B2-A audit_log canon

Architecture : couche_b · ADD ONLY · pas dict_item_history (B2-A)

Tables creees :
  couche_b.dict_price_references   -> vide au depart (mandate)
  couche_b.dict_uom_conversions    -> conversions UOM nerve center
  couche_b.dgmp_thresholds        -> seuils DGMP
  couche_b.dict_item_suppliers    -> item <-> supplier

Colonnes procurement_dict_items :
  item_type · default_uom · default_currency · unspsc_code
  classification_confidence · classification_source
  needs_review · quality_score · last_hash

Triggers :
  fn_dict_compute_hash()   BEFORE UPDATE -> last_hash (digest sha256)
  fn_dict_write_audit()    AFTER UPDATE  -> INSERT audit_log entity='DICT_ITEM'
  fn_compute_quality_score() BEFORE INSERT OR UPDATE

REGLE-12 : op.execute("SQL brut") uniquement
REGLE-41 : import sqlalchemy interdit
REGLE-N05 : audit_log append-only deja en place (038)
"""

from alembic import op

revision = "m7_3_dict_nerve_center"
down_revision = "m7_2_taxonomy_reset"
branch_labels = None
depends_on = None


def _add_col(schema, table, column, definition):
    """Ajoute une colonne si absente · idempotent."""
    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = '{schema}'
                  AND table_name   = '{table}'
                  AND column_name  = '{column}'
            ) THEN
                ALTER TABLE {schema}.{table}
                ADD COLUMN {column} {definition};
            END IF;
        END $$;
        """)


def upgrade() -> None:

    # ------------------------------------------------------------------
    # 1. Extension pgcrypto (deja presente via 038)
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # ------------------------------------------------------------------
    # 2. Tables couche_b
    # ------------------------------------------------------------------

    # dict_price_references · vide au depart (mandate)
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_b.dict_price_references (
            id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            item_id        TEXT        NOT NULL
                                   REFERENCES couche_b.procurement_dict_items(item_id)
                                   ON DELETE RESTRICT,
            uom_id         TEXT        NOT NULL
                                   REFERENCES couche_b.procurement_dict_units(unit_id)
                                   ON DELETE RESTRICT,
            currency       TEXT        NOT NULL DEFAULT 'XOF',
            source         TEXT        NOT NULL,
            period_label   TEXT        NOT NULL,
            price_value    NUMERIC(18,4) NOT NULL,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dict_price_ref_item
        ON couche_b.dict_price_references(item_id);
    """)

    # dict_uom_conversions · index NULL-safe
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_b.dict_uom_conversions (
            from_unit_id   TEXT        NOT NULL
                                   REFERENCES couche_b.procurement_dict_units(unit_id)
                                   ON DELETE RESTRICT,
            to_unit_id     TEXT        NOT NULL
                                   REFERENCES couche_b.procurement_dict_units(unit_id)
                                   ON DELETE RESTRICT,
            factor         NUMERIC(18,6) NOT NULL,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (from_unit_id, to_unit_id)
        );
    """)
    op.execute("DROP INDEX IF EXISTS couche_b.idx_dict_uom_conv_from;")
    op.execute("DROP INDEX IF EXISTS couche_b.idx_dict_uom_conv_to;")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dict_uom_conv_from
        ON couche_b.dict_uom_conversions(from_unit_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dict_uom_conv_to
        ON couche_b.dict_uom_conversions(to_unit_id);
    """)

    # dgmp_thresholds
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_b.dgmp_thresholds (
            id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            threshold_type TEXT        NOT NULL,
            value_min      NUMERIC(18,4),
            value_max      NUMERIC(18,4),
            currency       TEXT        NOT NULL DEFAULT 'XOF',
            active         BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    # dict_item_suppliers · item <-> vendor
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_b.dict_item_suppliers (
            id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            item_id        TEXT        NOT NULL
                                   REFERENCES couche_b.procurement_dict_items(item_id)
                                   ON DELETE RESTRICT,
            vendor_id      TEXT        NOT NULL,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (item_id, vendor_id)
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dict_item_supp_item
        ON couche_b.dict_item_suppliers(item_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dict_item_supp_vendor
        ON couche_b.dict_item_suppliers(vendor_id);
    """)

    # ------------------------------------------------------------------
    # 3. Colonnes procurement_dict_items
    # ------------------------------------------------------------------
    _add_col("couche_b", "procurement_dict_items", "item_type", "TEXT")
    _add_col("couche_b", "procurement_dict_items", "default_uom", "TEXT")
    _add_col(
        "couche_b", "procurement_dict_items", "default_currency", "TEXT DEFAULT 'XOF'"
    )
    _add_col("couche_b", "procurement_dict_items", "unspsc_code", "TEXT")
    _add_col(
        "couche_b",
        "procurement_dict_items",
        "classification_confidence",
        "NUMERIC(5,4)",
    )
    _add_col("couche_b", "procurement_dict_items", "classification_source", "TEXT")
    _add_col(
        "couche_b",
        "procurement_dict_items",
        "needs_review",
        "BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _add_col(
        "couche_b",
        "procurement_dict_items",
        "quality_score",
        "NUMERIC(5,4)",
    )
    _add_col("couche_b", "procurement_dict_items", "last_hash", "TEXT")

    # ------------------------------------------------------------------
    # 3b. fn_verify_audit_chain · fix plage partielle (prev init)
    # Quand from_seq > 1, prev doit etre event_hash du row precedent
    # ------------------------------------------------------------------
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
            IF p_from > 1 THEN
                SELECT event_hash INTO prev
                FROM audit_log
                WHERE chain_seq < p_from
                ORDER BY chain_seq DESC
                LIMIT 1;
                prev := COALESCE(prev, 'GENESIS');
            END IF;

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

    # ------------------------------------------------------------------
    # 4. fn_dict_compute_hash · BEFORE UPDATE
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION couche_b.fn_dict_compute_hash()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        DECLARE
            canon TEXT;
        BEGIN
            canon := COALESCE(NEW.item_id::text, '') || '|'
                  || COALESCE(NEW.label_fr, '') || '|'
                  || COALESCE(NEW.default_unit::text, '') || '|'
                  || COALESCE(NEW.domain_id::text, '') || '|'
                  || COALESCE(NEW.family_l2_id::text, '') || '|'
                  || COALESCE(NEW.subfamily_id::text, '') || '|'
                  || COALESCE(NEW.updated_at::text, '');
            NEW.last_hash := encode(digest(canon, 'sha256'), 'hex');
            RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_dict_compute_hash ON couche_b.procurement_dict_items;
    """)
    op.execute("""
        CREATE TRIGGER trg_dict_compute_hash
        BEFORE UPDATE ON couche_b.procurement_dict_items
        FOR EACH ROW EXECUTE FUNCTION couche_b.fn_dict_compute_hash();
    """)

    # ------------------------------------------------------------------
    # 5. fn_dict_write_audit · AFTER UPDATE -> audit_log (B2-A)
    # Alignement canon : entity, entity_id, action, payload_canonical,
    # prev_hash, event_hash (format fn_verify_audit_chain)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION couche_b.fn_dict_write_audit()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        DECLARE
            prev_h    TEXT;
            next_seq  BIGINT;
            ts        TIMESTAMPTZ := now();
            canon     TEXT;
            ev_hash   TEXT;
        BEGIN
            -- Sérialisation concurrence · même clé que write_event() logger.py:131
            PERFORM pg_advisory_xact_lock(
                ('x' || md5('audit_log:write_event'))::bit(64)::bigint
            );

            prev_h := 'GENESIS';
            SELECT event_hash INTO prev_h
            FROM public.audit_log
            ORDER BY chain_seq DESC
            LIMIT 1;
            prev_h := COALESCE(prev_h, 'GENESIS');

            next_seq := nextval('audit_log_chain_seq_seq');

            canon := COALESCE(NEW.item_id::text, '') || '|'
                  || COALESCE(NEW.label_fr, '') || '|'
                  || COALESCE(NEW.default_unit::text, '') || '|'
                  || COALESCE(NEW.domain_id::text, '') || '|'
                  || COALESCE(NEW.family_l2_id::text, '') || '|'
                  || COALESCE(NEW.subfamily_id::text, '') || '|'
                  || COALESCE(NEW.last_hash::text, '');

            ev_hash := encode(
                digest(
                    'DICT_ITEM' || NEW.item_id || 'UPDATE' || ''
                    || canon
                    || to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
                    || next_seq::text
                    || prev_h,
                    'sha256'
                ),
                'hex'
            );

            INSERT INTO public.audit_log (
                entity, entity_id, action, actor_id,
                payload, payload_canonical, prev_hash, event_hash,
                chain_seq, timestamp
            ) VALUES (
                'DICT_ITEM', NEW.item_id, 'UPDATE', NULL,
                jsonb_build_object(
                    'item_id', NEW.item_id,
                    'label_fr', NEW.label_fr,
                    'domain_id', NEW.domain_id,
                    'last_hash', NEW.last_hash
                ),
                canon,
                prev_h,
                ev_hash,
                next_seq,
                ts
            );

            RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_dict_write_audit ON couche_b.procurement_dict_items;
    """)
    op.execute("""
        CREATE TRIGGER trg_dict_write_audit
        AFTER UPDATE ON couche_b.procurement_dict_items
        FOR EACH ROW EXECUTE FUNCTION couche_b.fn_dict_write_audit();
    """)

    # ------------------------------------------------------------------
    # 6. fn_compute_quality_score · BEFORE INSERT OR UPDATE
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION couche_b.fn_compute_quality_score()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.quality_score := COALESCE(
                NEW.classification_confidence,
                NEW.confidence_score,
                0.5
            );
            RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_compute_quality_score ON couche_b.procurement_dict_items;
    """)
    op.execute("""
        CREATE TRIGGER trg_compute_quality_score
        BEFORE INSERT OR UPDATE ON couche_b.procurement_dict_items
        FOR EACH ROW EXECUTE FUNCTION couche_b.fn_compute_quality_score();
    """)

    # ------------------------------------------------------------------
    # 7. Verification fail-loud
    # ------------------------------------------------------------------
    op.execute("""
        DO $$
        DECLARE v INTEGER;
        BEGIN
            SELECT COUNT(*) INTO v
            FROM information_schema.tables
            WHERE table_schema = 'couche_b'
              AND table_name   = 'dict_price_references';
            IF v = 0 THEN
                RAISE EXCEPTION 'dict_price_references absent · M7.3 KO';
            END IF;

            SELECT COUNT(*) INTO v
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'last_hash';
            IF v = 0 THEN
                RAISE EXCEPTION 'last_hash absent de procurement_dict_items · M7.3 KO';
            END IF;

            RAISE NOTICE 'Migration M7.3 OK';
        END $$;
    """)


def downgrade() -> None:
    # Restore fn_verify_audit_chain original (sans fix plage partielle)
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
                IF computed <> rec.event_hash THEN RETURN FALSE; END IF;
                IF rec.prev_hash <> prev THEN RETURN FALSE; END IF;
                prev := rec.event_hash;
            END LOOP;
            RETURN TRUE;
        END;
        $$;
    """)

    # Triggers
    op.execute(
        "DROP TRIGGER IF EXISTS trg_compute_quality_score ON couche_b.procurement_dict_items;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_dict_write_audit ON couche_b.procurement_dict_items;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_dict_compute_hash ON couche_b.procurement_dict_items;"
    )

    # Functions
    op.execute("DROP FUNCTION IF EXISTS couche_b.fn_compute_quality_score();")
    op.execute("DROP FUNCTION IF EXISTS couche_b.fn_dict_write_audit();")
    op.execute("DROP FUNCTION IF EXISTS couche_b.fn_dict_compute_hash();")

    # Tables
    op.execute("DROP TABLE IF EXISTS couche_b.dict_item_suppliers;")
    op.execute("DROP TABLE IF EXISTS couche_b.dgmp_thresholds;")
    op.execute("DROP TABLE IF EXISTS couche_b.dict_uom_conversions;")
    op.execute("DROP TABLE IF EXISTS couche_b.dict_price_references;")

    # Columns (idempotent via DROP COLUMN IF EXISTS)
    for col in [
        "last_hash",
        "quality_score",
        "needs_review",
        "classification_source",
        "classification_confidence",
        "unspsc_code",
        "default_currency",
        "default_uom",
        "item_type",
    ]:
        op.execute(f"""
            ALTER TABLE couche_b.procurement_dict_items
            DROP COLUMN IF EXISTS {col};
            """)
