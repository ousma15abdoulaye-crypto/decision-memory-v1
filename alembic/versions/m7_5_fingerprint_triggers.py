"""m7_5 - fingerprint + triggers protection identite

Corrige :
  DEF-MRD3-03 : downgrade() fail-loud present ici
  DEF-MRD3-05 : colonne fingerprint absente - creee ici
  DEF-MRD3-06 : triggers protection absents - crees ici

Defintion fingerprint (peer review) :
  sha256(normalize(label_fr)|source_type)
  source_id EXCLU - identifiant pas identite
  source_type : mercuriale | imc | seed | manual | legacy | unknown

Cle item : item_id (TEXT) - PK existante
FK aliases : procurement_dict_aliases.item_id -> item_id

REGLE-12 : op.execute(SQL brut) uniquement
REGLE-T04 : zero DROP de colonne existante

Revision ID: m7_5_fingerprint_triggers
Revises: m7_4b
Create Date: 2026-03-09
"""

from alembic import op

revision = "m7_5_fingerprint_triggers"
down_revision = "m7_4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Colonne fingerprint ────────────────────────────────────────
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        ADD COLUMN IF NOT EXISTS fingerprint TEXT
    """)

    op.execute("""
        COMMENT ON COLUMN couche_b.procurement_dict_items.fingerprint IS
        'sha256(normalize(label_fr)|source_type) - source_id exclu'
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_dict_items_fingerprint_active
        ON couche_b.procurement_dict_items (fingerprint)
        WHERE active = TRUE AND fingerprint IS NOT NULL
    """)

    # ── 2. Colonnes tracabilite naissance ─────────────────────────────
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        ADD COLUMN IF NOT EXISTS birth_source TEXT
            CHECK (birth_source IN (
                'mercuriale', 'imc', 'seed', 'manual', 'legacy', 'unknown'
            )),
        ADD COLUMN IF NOT EXISTS birth_run_id UUID,
        ADD COLUMN IF NOT EXISTS birth_timestamp TIMESTAMPTZ DEFAULT now()
    """)

    # ── 3. Fonction + trigger trg_protect_item_identity ──────────────
    # Protege item_id et fingerprint apres initialisation
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

            RETURN NEW;
        END;
        $$
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_protect_item_identity
        ON couche_b.procurement_dict_items
    """)

    op.execute("""
        CREATE TRIGGER trg_protect_item_identity
        BEFORE UPDATE ON couche_b.procurement_dict_items
        FOR EACH ROW
        EXECUTE FUNCTION couche_b.fn_protect_item_identity()
    """)

    # ── 4. Fonction + trigger trg_protect_item_with_aliases ──────────
    # Interdit DELETE d'un item ayant des aliases
    # FK: procurement_dict_aliases.item_id -> item_id
    op.execute("""
        CREATE OR REPLACE FUNCTION couche_b.fn_protect_item_with_aliases()
        RETURNS TRIGGER
        LANGUAGE plpgsql AS $$
        DECLARE
            alias_count INT;
        BEGIN
            SELECT COUNT(*) INTO alias_count
            FROM couche_b.procurement_dict_aliases
            WHERE item_id = OLD.item_id;

            IF alias_count > 0 THEN
                RAISE EXCEPTION
                    '[INV-05] SUPPRESSION INTERDITE - '
                    'item_id=% possede % alias(es). '
                    'Supprimer les aliases avant suppression item.',
                    OLD.item_id, alias_count;
            END IF;

            RETURN OLD;
        END;
        $$
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_protect_item_with_aliases
        ON couche_b.procurement_dict_items
    """)

    op.execute("""
        CREATE TRIGGER trg_protect_item_with_aliases
        BEFORE DELETE ON couche_b.procurement_dict_items
        FOR EACH ROW
        EXECUTE FUNCTION couche_b.fn_protect_item_with_aliases()
    """)

    # ── 5. Verification fail-loud upgrade ─────────────────────────────
    op.execute("""
        DO $$
        DECLARE
            fp_col  TEXT;
            trg_id  TEXT;
            trg_ali TEXT;
        BEGIN
            SELECT column_name INTO fp_col
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'fingerprint';
            IF fp_col IS NULL THEN
                RAISE EXCEPTION 'm7_5 UPGRADE ECHOUE - fingerprint absente';
            END IF;

            SELECT trigger_name INTO trg_id
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
              AND trigger_name        = 'trg_protect_item_identity';
            IF trg_id IS NULL THEN
                RAISE EXCEPTION
                    'm7_5 UPGRADE ECHOUE - trg_protect_item_identity absent';
            END IF;

            SELECT trigger_name INTO trg_ali
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
              AND trigger_name        = 'trg_protect_item_with_aliases';
            IF trg_ali IS NULL THEN
                RAISE EXCEPTION
                    'm7_5 UPGRADE ECHOUE - trg_protect_item_with_aliases absent';
            END IF;

            RAISE NOTICE
                'm7_5 UPGRADE OK - fingerprint % trg_identity % trg_aliases %',
                fp_col, trg_id, trg_ali;
        END;
        $$
    """)


def downgrade() -> None:
    # ── Verification fail-loud AVANT downgrade (DEF-MRD3-03) ─────────
    op.execute("""
        DO $$
        DECLARE fp_col TEXT;
        BEGIN
            SELECT column_name INTO fp_col
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'fingerprint';
            IF fp_col IS NULL THEN
                RAISE EXCEPTION
                    'm7_5 DOWNGRADE - fingerprint absente avant downgrade - '
                    'etat incoherent - annuler';
            END IF;
        END;
        $$
    """)

    # ── Supprimer triggers et fonctions ──────────────────────────────
    op.execute("""
        DROP TRIGGER IF EXISTS trg_protect_item_with_aliases
        ON couche_b.procurement_dict_items
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_protect_item_identity
        ON couche_b.procurement_dict_items
    """)

    op.execute(
        "DROP FUNCTION IF EXISTS " "couche_b.fn_protect_item_with_aliases() CASCADE"
    )

    op.execute("DROP FUNCTION IF EXISTS " "couche_b.fn_protect_item_identity() CASCADE")

    # ── Supprimer index et colonne fingerprint ────────────────────────
    op.execute("""
        DROP INDEX IF EXISTS
        couche_b.ix_dict_items_fingerprint_active
    """)

    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        DROP COLUMN IF EXISTS fingerprint
    """)

    # ── Verification fail-loud APRES downgrade ────────────────────────
    op.execute("""
        DO $$
        DECLARE fp_col TEXT;
        BEGIN
            SELECT column_name INTO fp_col
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'fingerprint';
            IF fp_col IS NOT NULL THEN
                RAISE EXCEPTION
                    'm7_5 DOWNGRADE ECHOUE - fingerprint encore presente';
            END IF;
            RAISE NOTICE 'm7_5 DOWNGRADE OK';
        END;
        $$
    """)
