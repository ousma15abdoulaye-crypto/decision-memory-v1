"""046_imc_category_item_map

Revision ID: 046_imc_category_item_map
Revises: 045_agent_native_foundation
Create Date: 2026-03-15

DETTE-7 — Pont entre imc_entries (catégories INSTAT)
et couche_b.procurement_dict_items (dictionnaire DMS).

Fix PR #188 Copilot review :
  - ON DELETE CASCADE → ON DELETE RESTRICT (cohérence append-only)
  - Index fonctionnel LOWER(TRIM(category_raw)) pour perf jointures
  - Formule révision prix : P1 = P0 × (IMC_t1 / IMC_t0)
"""

from alembic import op

revision = "046_imc_category_item_map"
down_revision = "045_agent_native_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── Table pont imc_entries ↔ couche_b.procurement_dict_items ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS imc_category_item_map (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            category_raw   TEXT NOT NULL,
            item_id        TEXT NOT NULL
                           REFERENCES couche_b.procurement_dict_items(item_id)
                           ON DELETE RESTRICT,
            confidence     FLOAT NOT NULL
                           CHECK (confidence IN (0.6, 0.8, 1.0)),
            mapping_method TEXT NOT NULL DEFAULT 'manual'
                           CHECK (mapping_method IN (
                               'manual', 'fuzzy_auto', 'llm_suggested'
                           )),
            mapped_by      TEXT NOT NULL DEFAULT 'system',
            mapped_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            notes          TEXT,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (category_raw, item_id)
        );
    """)

    # Index btree standard sur item_id (UUID-like text)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_imc_map_item_id
            ON imc_category_item_map(item_id);
    """)

    # Index fonctionnel pour jointures LOWER(TRIM(category_raw))
    # Aligné avec les requêtes SQL du service imc_map.py
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_imc_map_category_norm
            ON imc_category_item_map(LOWER(TRIM(category_raw)));
    """)

    # Même index fonctionnel côté imc_entries pour symétrie jointure
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_imc_entries_category_norm
            ON imc_entries(LOWER(TRIM(category_raw)));
    """)

    # ── PROBE-SQL-01 : colonnes market_signals_v2 avant ALTER ──
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'market_signals_v2'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name  = 'market_signals_v2'
                AND   column_name = 'imc_revision_applied'
            ) THEN
                ALTER TABLE market_signals_v2
                    ADD COLUMN imc_revision_applied BOOLEAN     NOT NULL DEFAULT FALSE,
                    ADD COLUMN imc_revision_factor  FLOAT,
                    ADD COLUMN imc_revision_at      TIMESTAMPTZ;
            END IF;
        END$$;
    """)

    # ── Trigger append-only DELETE ──
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_imc_map_no_delete()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'imc_category_item_map est append-only. DELETE interdit.';
        END;
        $$;
    """)

    op.execute("""
        CREATE TRIGGER trg_imc_map_no_delete
            BEFORE DELETE ON imc_category_item_map
            FOR EACH ROW EXECUTE FUNCTION fn_imc_map_no_delete();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_imc_map_no_delete " "ON imc_category_item_map;"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_imc_map_no_delete();")
    op.execute("DROP INDEX IF EXISTS idx_imc_entries_category_norm;")
    op.execute("DROP INDEX IF EXISTS idx_imc_map_category_norm;")
    op.execute("DROP INDEX IF EXISTS idx_imc_map_item_id;")
    op.execute("DROP TABLE IF EXISTS imc_category_item_map;")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name  = 'market_signals_v2'
                AND   column_name = 'imc_revision_applied'
            ) THEN
                ALTER TABLE market_signals_v2
                    DROP COLUMN IF EXISTS imc_revision_applied,
                    DROP COLUMN IF EXISTS imc_revision_factor,
                    DROP COLUMN IF EXISTS imc_revision_at;
            END IF;
        END$$;
    """)
