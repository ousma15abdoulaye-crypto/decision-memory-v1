# -*- coding: utf-8 -*-
"""M-CRITERIA-TYPING — table criteria, enums, indexes, triggers.

Revision ID: 020_m_criteria_typing
Revises    : 019_consolidate_ec
Create Date: 2026-02-21

Constitution §6.3 — Critères evaluation AO Sahel.
cases.id est de type TEXT — case_id est donc TEXT (pas UUID).

Triggers :
  - enforce_criteria_weight_sum : DEFERRABLE INITIALLY DEFERRED
    verifie somme poids au COMMIT si case.status = 'evaluation'
  - enforce_canonical_item_ref  : BEFORE INSERT/UPDATE
    bypass si procurement_items absent (avant M-NORMALISATION-ITEMS)
"""
from __future__ import annotations

from alembic import op

revision      = "020_m_criteria_typing"
down_revision = "019_consolidate_ec"
branch_labels = None
depends_on    = None


def upgrade() -> None:

    # ── 1. ENUM criterion_category_enum ───────────────────────
    op.execute("""
        CREATE TYPE criterion_category_enum AS ENUM (
            'commercial',
            'capacity',
            'sustainability',
            'essential'
        )
    """)

    # ── 2. ENUM scoring_method_enum ───────────────────────────
    op.execute("""
        CREATE TYPE scoring_method_enum AS ENUM (
            'formula',
            'points_scale',
            'judgment',
            'paliers'
        )
    """)

    # ── 3. TABLE criteria ─────────────────────────────────────
    # cases.id est TEXT (detecte Etape 0) — case_id est TEXT.
    op.execute("""
        CREATE TABLE criteria (
            id                UUID PRIMARY KEY
                              DEFAULT gen_random_uuid(),
            case_id           TEXT NOT NULL
                              REFERENCES cases(id)
                              ON DELETE CASCADE,
            org_id            TEXT NOT NULL,
            label             TEXT NOT NULL,
            category          criterion_category_enum NOT NULL,
            weight_pct        NUMERIC(5,2) NOT NULL
                                  CHECK (weight_pct >= 0
                                     AND weight_pct <= 100),
            min_weight_pct    NUMERIC(5,2)
                                  CHECK (min_weight_pct IS NULL
                                      OR min_weight_pct >= 0),
            is_essential      BOOLEAN NOT NULL DEFAULT FALSE,
            threshold         NUMERIC(10,4),
            scoring_method    scoring_method_enum NOT NULL,
            canonical_item_id TEXT,
            currency          TEXT NOT NULL DEFAULT 'XOF',
            description       TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ── 4. INDEX ──────────────────────────────────────────────
    op.execute("""
        CREATE INDEX idx_criteria_case_id
            ON criteria(case_id)
    """)

    op.execute("""
        CREATE INDEX idx_criteria_org_id
            ON criteria(org_id)
    """)

    op.execute("""
        CREATE INDEX idx_criteria_canonical_item
            ON criteria(canonical_item_id)
            WHERE canonical_item_id IS NOT NULL
    """)

    # ── 5. TRIGGER poids = 100% — DEFERRABLE ─────────────────
    # DEFERRABLE INITIALLY DEFERRED :
    #   Verifie au COMMIT, pas a chaque INSERT individuel.
    #   Permet d'inserer plusieurs criteres dans une meme
    #   transaction avant que la somme soit validee.
    #   Actif uniquement si case.status = 'evaluation'.
    op.execute("""
        CREATE OR REPLACE FUNCTION check_criteria_weight_sum()
        RETURNS TRIGGER AS $$
        DECLARE
            v_case_id     TEXT;
            v_case_status TEXT;
            v_total       NUMERIC;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                v_case_id := OLD.case_id;
            ELSE
                v_case_id := NEW.case_id;
            END IF;

            SELECT status INTO v_case_status
            FROM cases WHERE id = v_case_id;

            IF v_case_status != 'evaluation' THEN
                RETURN NEW;
            END IF;

            SELECT COALESCE(SUM(weight_pct), 0)
            INTO v_total
            FROM criteria
            WHERE case_id      = v_case_id
              AND is_essential = FALSE;

            IF v_total < 99.99 OR v_total > 100.01 THEN
                RAISE EXCEPTION
                    'CRITERIA-WEIGHT-SUM: somme poids '
                    'non-essentiels = % pour case_id %. '
                    'Doit etre 100%%. Constitution 6.3.',
                    v_total, v_case_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE CONSTRAINT TRIGGER enforce_criteria_weight_sum
        AFTER INSERT OR UPDATE OR DELETE
        ON criteria
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION check_criteria_weight_sum()
    """)

    # ── 6. TRIGGER canonical_item_id ─────────────────────────
    # Bypass si procurement_items n'existe pas encore.
    # Actif apres M-NORMALISATION-ITEMS.
    op.execute("""
        CREATE OR REPLACE FUNCTION check_canonical_item_exists()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.canonical_item_id IS NULL THEN
                RETURN NEW;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name   = 'procurement_items'
            ) THEN
                RETURN NEW;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM procurement_items
                WHERE id = NEW.canonical_item_id
            ) THEN
                RAISE EXCEPTION
                    'CANONICAL-ITEM-NOT-FOUND: '
                    'canonical_item_id % absent de '
                    'procurement_items. ADR-0002 §2.1.',
                    NEW.canonical_item_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER enforce_canonical_item_ref
        BEFORE INSERT OR UPDATE ON criteria
        FOR EACH ROW
        EXECUTE FUNCTION check_canonical_item_exists()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS enforce_canonical_item_ref "
        "ON criteria"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS enforce_criteria_weight_sum "
        "ON criteria"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS check_canonical_item_exists()"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS check_criteria_weight_sum()"
    )
    op.execute("DROP TABLE IF EXISTS criteria")
    op.execute("DROP TYPE IF EXISTS criterion_category_enum")
    op.execute("DROP TYPE IF EXISTS scoring_method_enum")
