"""
M7.3b · Dépréciation familles legacy M6.

DÉCISION : ADR-0016
  family_id = READ-ONLY historique après cette migration
  Nouvelles écritures → domain_id/family_l2_id/subfamily_id (M7.2)
  Tables legacy conservées (RÈGLE-T04) · jamais DROP

PIÈGE-M7-04 : deux triggers séparés INSERT / UPDATE
  OLD absent sur INSERT → trigger INSERT sans WHEN sur OLD
"""

from alembic import op

revision = "m7_3b_deprecate_legacy_families"
down_revision = "m7_3_dict_nerve_center"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # 0 · Autoriser family_id NULL pour nouveaux items (M7.2 cible)
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        ALTER COLUMN family_id DROP NOT NULL
    """)

    # 1 · Marquer procurement_dict_families comme deprecated
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_families
        ADD COLUMN IF NOT EXISTS deprecated
            BOOLEAN NOT NULL DEFAULT TRUE
    """)
    op.execute("""
        COMMENT ON TABLE couche_b.procurement_dict_families IS
        'DEPRECATED M7.3b — artefact M6.
         Référence : ADR-0016.
         Source de vérité : taxo_l1_domains/taxo_l2_families/taxo_l3_subfamilies'
    """)
    op.execute("""
        COMMENT ON COLUMN couche_b.procurement_dict_items.family_id IS
        'LEGACY M6 — READ-ONLY historique.
         Référence : ADR-0016 · RÈGLE-DICT-01.
         Utiliser domain_id / family_l2_id / subfamily_id (M7.2)'
    """)

    # 2 · Fonction de blocage
    op.execute("""
        CREATE OR REPLACE FUNCTION
            couche_b.fn_block_legacy_family_write()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'LEGACY family_id interdit après M7.3b (ADR-0016). '
                'Utiliser domain_id/family_l2_id/subfamily_id. '
                'item_id: %',
                NEW.item_id;
        END;
        $$
    """)

    # 3 · Trigger INSERT · OLD absent sur INSERT · PIÈGE-M7-04
    op.execute("""
        DROP TRIGGER IF EXISTS trg_block_legacy_family_insert
        ON couche_b.procurement_dict_items
    """)
    op.execute("""
        CREATE TRIGGER trg_block_legacy_family_insert
        BEFORE INSERT
        ON couche_b.procurement_dict_items
        FOR EACH ROW
        WHEN (NEW.family_id IS NOT NULL)
        EXECUTE FUNCTION couche_b.fn_block_legacy_family_write()
    """)

    # 4 · Trigger UPDATE · OLD disponible · sécurisé
    op.execute("""
        DROP TRIGGER IF EXISTS trg_block_legacy_family_update
        ON couche_b.procurement_dict_items
    """)
    op.execute("""
        CREATE TRIGGER trg_block_legacy_family_update
        BEFORE UPDATE OF family_id
        ON couche_b.procurement_dict_items
        FOR EACH ROW
        WHEN (OLD.family_id IS DISTINCT FROM NEW.family_id)
        EXECUTE FUNCTION couche_b.fn_block_legacy_family_write()
    """)

    # 5 · Vue lecture seule historique
    op.execute("""
        CREATE OR REPLACE VIEW
            couche_b.legacy_procurement_families AS
        SELECT
            family_id,
            label_fr,
            criticite,
            deprecated,
            'DEPRECATED_M7.3b_ADR-0016' AS status_note
        FROM couche_b.procurement_dict_families
    """)

    # 6 · Vérification fail-loud
    op.execute("""
        DO $$
        DECLARE
            v_insert INTEGER;
            v_update INTEGER;
        BEGIN
            SELECT COUNT(*) INTO v_insert
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
              AND trigger_name = 'trg_block_legacy_family_insert';

            SELECT COUNT(*) INTO v_update
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
              AND trigger_name = 'trg_block_legacy_family_update';

            IF v_insert = 0 THEN
                RAISE EXCEPTION
                    'trg_block_legacy_family_insert absent — M7.3b KO';
            END IF;
            IF v_update = 0 THEN
                RAISE EXCEPTION
                    'trg_block_legacy_family_update absent — M7.3b KO';
            END IF;

            RAISE NOTICE
                'M7.3b OK — triggers legacy INSERT+UPDATE actifs (ADR-0016)';
        END;
        $$
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_block_legacy_family_update
        ON couche_b.procurement_dict_items
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_block_legacy_family_insert
        ON couche_b.procurement_dict_items
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
            couche_b.fn_block_legacy_family_write() CASCADE
    """)
    op.execute("""
        DROP VIEW IF EXISTS couche_b.legacy_procurement_families
    """)
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_families
        DROP COLUMN IF EXISTS deprecated
    """)
    # D2 · family_id DROP NOT NULL idempotent · évite erreur cycle downgrade
    op.execute("""
        DO $$
        DECLARE
            v_nullable TEXT;
        BEGIN
            SELECT is_nullable INTO v_nullable
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'family_id';

            IF v_nullable = 'NO' THEN
                EXECUTE 'ALTER TABLE couche_b.procurement_dict_items ALTER COLUMN family_id DROP NOT NULL';
            END IF;
        END;
        $$
    """)
