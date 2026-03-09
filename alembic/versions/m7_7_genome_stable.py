"""m7_7 - Genome stable : label_status + taxo + collision append-only

BRIQUE-1 : colonnes taxo_l1/l2/l3 (taxo_version deja presente)
BRIQUE-2 : label_status + protection label_fr si validated
BRIQUE-3 : trigger append-only sur dict_collision_log (public)

Schema reel :
  item_id    = PK TEXT (pas item_uid)
  label_fr   = colonne label (pas label)
  taxo_version = deja presente — ne pas recreer
  dict_collision_log dans public — ne pas recreer

REGLE-12  : op.execute(SQL brut) uniquement
REGLE-T04 : zero DROP de colonne existante

Revision ID: m7_7_genome_stable
Revises: m7_6_item_code
Create Date: 2026-03-09
"""

from alembic import op

revision = "m7_7_genome_stable"
down_revision = "m7_6_item_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── BRIQUE-2 : label_status ───────────────────────────────────────
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        ADD COLUMN IF NOT EXISTS label_status TEXT
            NOT NULL DEFAULT 'draft'
            CHECK (label_status IN ('draft', 'validated', 'deprecated'))
    """)

    op.execute("""
        COMMENT ON COLUMN couche_b.procurement_dict_items.label_status IS
        'draft | validated | deprecated - label_fr immuable si validated'
    """)

    # ── BRIQUE-1 : colonnes taxo (taxo_version deja presente) ─────────
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        ADD COLUMN IF NOT EXISTS taxo_l1 TEXT,
        ADD COLUMN IF NOT EXISTS taxo_l2 TEXT,
        ADD COLUMN IF NOT EXISTS taxo_l3 TEXT
    """)

    # ── BRIQUE-2 : etendre fn_protect_item_identity ───────────────────
    # Utilise item_id (PK reel) et label_fr (colonne label reelle)
    op.execute("""
        CREATE OR REPLACE FUNCTION couche_b.fn_protect_item_identity()
        RETURNS TRIGGER
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.item_id IS DISTINCT FROM OLD.item_id THEN
                RAISE EXCEPTION
                    '[INV-04] item_id immuable - '
                    'tentative modification item_id=% -> %',
                    OLD.item_id, NEW.item_id;
            END IF;

            IF OLD.fingerprint IS NOT NULL
               AND NEW.fingerprint IS DISTINCT FROM OLD.fingerprint
            THEN
                RAISE EXCEPTION
                    '[INV-04] fingerprint immuable - item_id=%',
                    OLD.item_id;
            END IF;

            IF OLD.item_code IS NOT NULL
               AND NEW.item_code IS DISTINCT FROM OLD.item_code
            THEN
                RAISE EXCEPTION
                    '[IS-10] item_code immuable - item_id=%',
                    OLD.item_id;
            END IF;

            IF OLD.label_status = 'validated'
               AND NEW.label_fr IS DISTINCT FROM OLD.label_fr
            THEN
                RAISE EXCEPTION
                    '[BRIQUE-2] label_fr immuable apres validation - '
                    'item_id=%. Creer un alias pour corriger.',
                    OLD.item_id;
            END IF;

            IF OLD.label_status = 'deprecated'
               AND NEW.label_status != 'deprecated'
            THEN
                RAISE EXCEPTION
                    '[BRIQUE-2] label_status deprecated '
                    'irreversible - item_id=%',
                    OLD.item_id;
            END IF;

            RETURN NEW;
        END;
        $$
    """)

    # ── BRIQUE-3 : trigger append-only sur dict_collision_log (public) ─
    # La table existe deja dans public - ajouter seulement le trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION
        couche_b.fn_collision_log_append_only()
        RETURNS TRIGGER
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION
                    'dict_collision_log append-only - DELETE interdit';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.raw_text_1 IS DISTINCT FROM NEW.raw_text_1
                   OR OLD.raw_text_2 IS DISTINCT FROM NEW.raw_text_2
                   OR OLD.fuzzy_score IS DISTINCT FROM NEW.fuzzy_score
                THEN
                    RAISE EXCEPTION
                        'dict_collision_log - seuls resolution '
                        'et resolved_by sont modifiables';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_collision_log_append_only
        ON public.dict_collision_log
    """)

    op.execute("""
        CREATE TRIGGER trg_collision_log_append_only
        BEFORE DELETE OR UPDATE ON public.dict_collision_log
        FOR EACH ROW
        EXECUTE FUNCTION couche_b.fn_collision_log_append_only()
    """)

    # ── Verification fail-loud upgrade ────────────────────────────────
    op.execute("""
        DO $$
        DECLARE
            ls_col TEXT;
            t1_col TEXT;
        BEGIN
            SELECT column_name INTO ls_col
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'label_status';
            IF ls_col IS NULL THEN
                RAISE EXCEPTION
                    'm7_7 UPGRADE ECHOUE - label_status absente';
            END IF;

            SELECT column_name INTO t1_col
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'taxo_l1';
            IF t1_col IS NULL THEN
                RAISE EXCEPTION
                    'm7_7 UPGRADE ECHOUE - taxo_l1 absente';
            END IF;

            RAISE NOTICE
                'm7_7 UPGRADE OK - label_status % taxo_l1 %',
                ls_col, t1_col;
        END;
        $$
    """)


def downgrade() -> None:
    # ── Verification fail-loud AVANT downgrade ────────────────────────
    op.execute("""
        DO $$
        DECLARE col TEXT;
        BEGIN
            SELECT column_name INTO col
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'label_status';
            IF col IS NULL THEN
                RAISE EXCEPTION
                    'm7_7 DOWNGRADE - label_status absente - '
                    'etat incoherent';
            END IF;
        END;
        $$
    """)

    # ── Supprimer trigger collision log ──────────────────────────────
    op.execute("""
        DROP TRIGGER IF EXISTS trg_collision_log_append_only
        ON public.dict_collision_log
    """)

    op.execute(
        "DROP FUNCTION IF EXISTS " "couche_b.fn_collision_log_append_only() CASCADE"
    )

    # ── Supprimer taxo colonnes ajoutees ──────────────────────────────
    # taxo_version est pre-existante - ne pas toucher (REGLE-T04)
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        DROP COLUMN IF EXISTS taxo_l3,
        DROP COLUMN IF EXISTS taxo_l2,
        DROP COLUMN IF EXISTS taxo_l1
    """)

    # ── Restaurer fn_protect_item_identity sans label_status ─────────
    op.execute("""
        CREATE OR REPLACE FUNCTION couche_b.fn_protect_item_identity()
        RETURNS TRIGGER
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.item_id IS DISTINCT FROM OLD.item_id THEN
                RAISE EXCEPTION
                    '[INV-04] item_id immuable - '
                    'item_id=% -> %',
                    OLD.item_id, NEW.item_id;
            END IF;
            IF OLD.fingerprint IS NOT NULL
               AND NEW.fingerprint IS DISTINCT FROM OLD.fingerprint
            THEN
                RAISE EXCEPTION
                    '[INV-04] fingerprint immuable - item_id=%',
                    OLD.item_id;
            END IF;
            IF OLD.item_code IS NOT NULL
               AND NEW.item_code IS DISTINCT FROM OLD.item_code
            THEN
                RAISE EXCEPTION
                    '[IS-10] item_code immuable - item_id=%',
                    OLD.item_id;
            END IF;
            RETURN NEW;
        END;
        $$
    """)

    # ── Supprimer label_status ────────────────────────────────────────
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        DROP COLUMN IF EXISTS label_status
    """)

    # ── Verification fail-loud APRES downgrade ────────────────────────
    op.execute("""
        DO $$
        DECLARE col TEXT;
        BEGIN
            SELECT column_name INTO col
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'label_status';
            IF col IS NOT NULL THEN
                RAISE EXCEPTION
                    'm7_7 DOWNGRADE ECHOUE - label_status encore presente';
            END IF;
            RAISE NOTICE 'm7_7 DOWNGRADE OK';
        END;
        $$
    """)
