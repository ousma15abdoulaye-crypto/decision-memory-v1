"""046b_imc_map_fix_restrict_indexes

Revision ID: 046b_imc_map_fix_restrict_indexes
Revises: 046_imc_category_item_map
Create Date: 2026-03-15

Migration corrective — DB déjà en ancienne 046 (FK CASCADE + index btree).
Idempotente : PROBE-SQL-01 avant chaque opération.

Corrections :
  1. FK item_id : CASCADE → RESTRICT
  2. idx_imc_map_category_raw (btree) → idx_imc_map_category_norm (fonctionnel)
  3. idx_imc_entries_category_norm (fonctionnel) si absent
"""

from alembic import op

revision = "046b_imc_map_fix_restrict_indexes"
down_revision = "046_imc_category_item_map"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── 1. FK CASCADE → RESTRICT ──────────────────────────
    # PROBE : vérifier si FK existe et si elle est CASCADE
    op.execute("""
        DO $$
        DECLARE
            v_conname TEXT;
            v_deltype TEXT;
        BEGIN
            SELECT c.conname, c.confdeltype
              INTO v_conname, v_deltype
              FROM pg_constraint c
              JOIN pg_class t ON t.oid = c.conrelid
             WHERE t.relname = 'imc_category_item_map'
               AND c.contype = 'f'
               AND c.conname LIKE '%item_id%'
             LIMIT 1;

            -- Si CASCADE (confdeltype = 'c') → corriger
            IF v_deltype = 'c' THEN
                EXECUTE format(
                    'ALTER TABLE imc_category_item_map
                     DROP CONSTRAINT %I', v_conname
                );
                ALTER TABLE imc_category_item_map
                    ADD CONSTRAINT imc_map_item_id_fk
                    FOREIGN KEY (item_id)
                    REFERENCES couche_b.procurement_dict_items(item_id)
                    ON DELETE RESTRICT;
                RAISE NOTICE 'FK corrigée CASCADE → RESTRICT';
            ELSE
                RAISE NOTICE 'FK déjà RESTRICT — aucune action';
            END IF;
        END$$;
    """)

    # ── 2. Index btree → index fonctionnel category_norm ──
    # DROP ancien index btree si présent
    op.execute("""
        DROP INDEX IF EXISTS idx_imc_map_category_raw;
    """)

    # CREATE index fonctionnel (idempotent via IF NOT EXISTS)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_imc_map_category_norm
            ON imc_category_item_map(LOWER(TRIM(category_raw)));
    """)

    # ── 3. Index fonctionnel imc_entries ──────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_imc_entries_category_norm
            ON imc_entries(LOWER(TRIM(category_raw)));
    """)


def downgrade() -> None:
    # Restaurer état ancienne 046 si rollback nécessaire
    op.execute("DROP INDEX IF EXISTS idx_imc_entries_category_norm;")
    op.execute("DROP INDEX IF EXISTS idx_imc_map_category_norm;")
    op.execute("""
        DO $$
        DECLARE
            v_conname TEXT;
            v_deltype TEXT;
        BEGIN
            SELECT c.conname, c.confdeltype
              INTO v_conname, v_deltype
              FROM pg_constraint c
              JOIN pg_class t ON t.oid = c.conrelid
             WHERE t.relname = 'imc_category_item_map'
               AND c.contype = 'f'
             LIMIT 1;

            IF v_deltype = 'r' THEN
                EXECUTE format(
                    'ALTER TABLE imc_category_item_map
                     DROP CONSTRAINT %I', v_conname
                );
                ALTER TABLE imc_category_item_map
                    ADD CONSTRAINT imc_map_item_id_fk_cascade
                    FOREIGN KEY (item_id)
                    REFERENCES couche_b.procurement_dict_items(item_id)
                    ON DELETE CASCADE;
                RAISE NOTICE 'FK restaurée RESTRICT → CASCADE';
            END IF;
        END$$;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_imc_map_category_raw
            ON imc_category_item_map(category_raw);
    """)
