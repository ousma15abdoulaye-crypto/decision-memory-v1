"""
M7.4a - Doctrine identite items procurement.

Ajoute sur couche_b.procurement_dict_items :
  item_uid              TEXT UNIQUE   UUIDv7 - ancre technique immuable
  item_code             TEXT UNIQUE   ITM.BD.BF.BS.SERIAL.CD - ancre metier
  birth_domain_id       TEXT          lineage naissance - immuable
  birth_family_l2_id    TEXT          lineage naissance - immuable
  birth_subfamily_id    TEXT          lineage naissance - immuable
  id_version            TEXT NOT NULL version convention - defaut '1.0'
  llm_domain_id_raw     TEXT          raw LLM avant validation - audit
  llm_family_l2_id_raw  TEXT          raw LLM avant validation - audit
  llm_subfamily_id_raw  TEXT          raw LLM avant validation - audit

Backfill initial seeds uniquement (domain_id non null + human_validated).
Items terrain sans taxonomie : birth_* = NULL. Correct.

REGLE-T04  : zero DROP
REGLE-12   : SQL brut uniquement
REGLE-ID03 : jamais ecraser identite existante
"""
from alembic import op

revision = "m7_4a_item_identity_doctrine"
down_revision = "m7_4_dict_vivant"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # 1 - Colonnes identite technique, metier, lineage, audit LLM
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
            ADD COLUMN IF NOT EXISTS item_uid
                TEXT,
            ADD COLUMN IF NOT EXISTS item_code
                TEXT,
            ADD COLUMN IF NOT EXISTS birth_domain_id
                TEXT,
            ADD COLUMN IF NOT EXISTS birth_family_l2_id
                TEXT,
            ADD COLUMN IF NOT EXISTS birth_subfamily_id
                TEXT,
            ADD COLUMN IF NOT EXISTS id_version
                TEXT NOT NULL DEFAULT '1.0',
            ADD COLUMN IF NOT EXISTS llm_domain_id_raw
                TEXT,
            ADD COLUMN IF NOT EXISTS llm_family_l2_id_raw
                TEXT,
            ADD COLUMN IF NOT EXISTS llm_subfamily_id_raw
                TEXT
    """)

    # 2 - Contrainte unicite item_uid
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_dict_items_item_uid'
                  AND conrelid = 'couche_b.procurement_dict_items'::regclass
            ) THEN
                ALTER TABLE couche_b.procurement_dict_items
                    ADD CONSTRAINT uq_dict_items_item_uid
                    UNIQUE (item_uid);
            END IF;
        END;
        $$
    """)

    # 3 - Contrainte unicite item_code
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_dict_items_item_code'
                  AND conrelid = 'couche_b.procurement_dict_items'::regclass
            ) THEN
                ALTER TABLE couche_b.procurement_dict_items
                    ADD CONSTRAINT uq_dict_items_item_code
                    UNIQUE (item_code);
            END IF;
        END;
        $$
    """)

    # 4 - Index performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dict_items_item_uid
        ON couche_b.procurement_dict_items (item_uid)
        WHERE item_uid IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dict_items_item_code
        ON couche_b.procurement_dict_items (item_code)
        WHERE item_code IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dict_items_birth_subfamily
        ON couche_b.procurement_dict_items (birth_subfamily_id)
        WHERE birth_subfamily_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dict_items_subfamily
        ON couche_b.procurement_dict_items (subfamily_id)
        WHERE subfamily_id IS NOT NULL
    """)

    # 5 - Backfill birth lineage - seeds uniquement - jamais fabriquer du faux
    #     Condition : human_validated=TRUE ET domain_id deja rempli
    #     Items terrain sans taxonomie -> birth_* reste NULL - correct (REGLE-ID04)
    op.execute("""
        UPDATE couche_b.procurement_dict_items
        SET
            birth_domain_id    = domain_id,
            birth_family_l2_id = family_l2_id,
            birth_subfamily_id = subfamily_id
        WHERE human_validated  = TRUE
          AND domain_id        IS NOT NULL
          AND birth_domain_id  IS NULL
    """)

    # 6 - Commentaires colonnes
    op.execute("""
        COMMENT ON COLUMN couche_b.procurement_dict_items.item_uid IS
        'Ancre technique immuable. UUIDv7. RFC 9562.
         Genere localement. Jamais reassigne. Jamais tiers.
         Doctrine M7.4a.'
    """)
    op.execute("""
        COMMENT ON COLUMN couche_b.procurement_dict_items.item_code IS
        'Ancre metier stable DMS. Format ITM.BD.BF.BS.SERIAL.CD.
         Check digit Luhn mod 10. Attribue une fois. Jamais recycle.
         NULL si birth lineage incomplet. Doctrine M7.4a.'
    """)
    op.execute("""
        COMMENT ON COLUMN couche_b.procurement_dict_items.birth_domain_id IS
        'Lineage naissance. Immuable apres premiere canonisation.
         Separe de domain_id courant (mutable). Doctrine M7.4a.'
    """)
    op.execute("""
        COMMENT ON COLUMN couche_b.procurement_dict_items.llm_domain_id_raw IS
        'Raw LLM avant validation Pydantic. Conserve pour audit.
         Peut contenir des codes inventes. Jamais efface. Doctrine M7.4a.'
    """)

    # 7 - Verification fail-loud
    op.execute("""
        DO $$
        DECLARE
            v_uid   INTEGER := 0;
            v_code  INTEGER := 0;
            v_birth INTEGER := 0;
            v_seeds INTEGER := 0;
        BEGIN
            SELECT COUNT(*) INTO v_uid
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'item_uid';

            SELECT COUNT(*) INTO v_code
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'item_code';

            SELECT COUNT(*) INTO v_birth
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'birth_domain_id';

            SELECT COUNT(*) INTO v_seeds
            FROM couche_b.procurement_dict_items
            WHERE human_validated = TRUE AND active = TRUE;

            IF v_uid  = 0 THEN RAISE EXCEPTION 'M7.4a ABORT: item_uid absent';      END IF;
            IF v_code = 0 THEN RAISE EXCEPTION 'M7.4a ABORT: item_code absent';     END IF;
            IF v_birth= 0 THEN RAISE EXCEPTION 'M7.4a ABORT: birth_domain_id absent'; END IF;
            IF v_seeds != 51 THEN
                RAISE EXCEPTION 'M7.4a ABORT: seed count % != 51', v_seeds;
            END IF;

            RAISE NOTICE
                'M7.4a OK - colonnes identite presentes - seeds=51';
        END;
        $$
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS couche_b.idx_dict_items_item_uid")
    op.execute("DROP INDEX IF EXISTS couche_b.idx_dict_items_item_code")
    op.execute("DROP INDEX IF EXISTS couche_b.idx_dict_items_birth_subfamily")
    op.execute("DROP INDEX IF EXISTS couche_b.idx_dict_items_subfamily")
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE couche_b.procurement_dict_items
                DROP CONSTRAINT IF EXISTS uq_dict_items_item_uid,
                DROP CONSTRAINT IF EXISTS uq_dict_items_item_code;
        EXCEPTION WHEN others THEN NULL;
        END;
        $$
    """)
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
            DROP COLUMN IF EXISTS item_uid,
            DROP COLUMN IF EXISTS item_code,
            DROP COLUMN IF EXISTS birth_domain_id,
            DROP COLUMN IF EXISTS birth_family_l2_id,
            DROP COLUMN IF EXISTS birth_subfamily_id,
            DROP COLUMN IF EXISTS id_version,
            DROP COLUMN IF EXISTS llm_domain_id_raw,
            DROP COLUMN IF EXISTS llm_family_l2_id_raw,
            DROP COLUMN IF EXISTS llm_subfamily_id_raw
    """)
