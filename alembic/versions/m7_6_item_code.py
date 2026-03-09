"""m7_6 - item_code : code lisible deterministe

Ajoute la colonne item_code sur couche_b.procurement_dict_items.
Format : {PREFIX}-{YYYYMM}-{SEQ6}
Backfill : scripts/mrd5_backfill_item_code.py

Schema reel :
  item_id (PK TEXT) - pas item_uid
  label_fr - colonne label reelle
  trg_protect_item_identity etendu avec protection item_code

REGLE-12  : op.execute(SQL brut) uniquement
REGLE-T04 : zero DROP de colonne existante

Revision ID: m7_6_item_code
Revises: m7_5_fingerprint_triggers
Create Date: 2026-03-09
"""

from alembic import op

revision = "m7_6_item_code"
down_revision = "m7_5_fingerprint_triggers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Colonne item_code ──────────────────────────────────────────
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        ADD COLUMN IF NOT EXISTS item_code TEXT
    """)

    op.execute("""
        COMMENT ON COLUMN couche_b.procurement_dict_items.item_code IS
        'Code lisible {PREFIX}-{YYYYMM}-{SEQ6}. Immuable apres creation.'
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_dict_items_item_code_active
        ON couche_b.procurement_dict_items (item_code)
        WHERE active = TRUE AND item_code IS NOT NULL
    """)

    # ── 2. Etendre fn_protect_item_identity avec item_code ────────────
    # Utilise item_id (PK reel) - item_uid n'existe pas dans ce schema
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
                    '[INV-04] fingerprint immuable apres initialisation - '
                    'item_id=%',
                    OLD.item_id;
            END IF;

            IF OLD.item_code IS NOT NULL
               AND NEW.item_code IS DISTINCT FROM OLD.item_code
            THEN
                RAISE EXCEPTION
                    '[IS-10] item_code immuable apres creation - '
                    'item_id=% item_code=%',
                    OLD.item_id, OLD.item_code;
            END IF;

            RETURN NEW;
        END;
        $$
    """)

    # ── 3. Verification fail-loud upgrade ─────────────────────────────
    op.execute("""
        DO $$
        DECLARE col TEXT;
        BEGIN
            SELECT column_name INTO col
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'item_code';
            IF col IS NULL THEN
                RAISE EXCEPTION 'm7_6 UPGRADE ECHOUE - item_code absente';
            END IF;
            RAISE NOTICE 'm7_6 UPGRADE OK - item_code %', col;
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
              AND column_name  = 'item_code';
            IF col IS NULL THEN
                RAISE EXCEPTION
                    'm7_6 DOWNGRADE - item_code absente avant downgrade - '
                    'etat incoherent';
            END IF;
        END;
        $$
    """)

    # ── Restaurer fn_protect_item_identity sans item_code ────────────
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
            RETURN NEW;
        END;
        $$
    """)

    # ── Supprimer index et colonne item_code ──────────────────────────
    op.execute("""
        DROP INDEX IF EXISTS couche_b.ix_dict_items_item_code_active
    """)

    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        DROP COLUMN IF EXISTS item_code
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
              AND column_name  = 'item_code';
            IF col IS NOT NULL THEN
                RAISE EXCEPTION
                    'm7_6 DOWNGRADE ECHOUE - item_code encore presente';
            END IF;
            RAISE NOTICE 'm7_6 DOWNGRADE OK';
        END;
        $$
    """)
