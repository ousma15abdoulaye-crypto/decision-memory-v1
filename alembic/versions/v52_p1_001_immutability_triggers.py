"""v52_p1_001 — Triggers d'immutabilité (INV-W05, INV-S03 étendu).

Revision ID: v52_p1_001_immutability_triggers
Revises: 093_v51_assessment_history
Branch labels: None
Depends on: None

Ajoute les triggers manquants après audit Railway 2026-04-09.

TRIGGERS DÉJÀ EN PLACE — non touchés par cette migration :
  - deliberation_messages : trg_dm_append_only (fn_reject_mutation) → INV-S03 ✓
  - assessment_comments   : trg_ac_content_immutable (fn_ac_content_immutable)
                            protège content + is_flag → INV-S04 ✓

TRIGGERS AJOUTÉS par cette migration :
  1. committee_sessions — colonne pv_snapshot immutable (INV-W05)
     pv_snapshot est une colonne JSONB dans committee_sessions (pas une table).
     Une fois positionné (NOT NULL), toute tentative de modification est rejetée.
  2. assessment_history  — append-only (INV-S03 étendu)
     Aucun trigger n'existait sur cette table.

REGLE-12 : op.execute() uniquement — jamais autogenerate.
"""

from __future__ import annotations

from alembic import op

revision = "v52_p1_001_immutability_triggers"
down_revision = "093_v51_assessment_history"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ------------------------------------------------------------------
    # TRIGGER 1 — committee_sessions.pv_snapshot immutable (INV-W05)
    #
    # pv_snapshot est une colonne JSONB (pas une table séparée).
    # Une fois scellée (NOT NULL), elle ne peut plus être modifiée ni
    # remise à NULL.
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_fn_pv_snapshot_immutable()
        RETURNS trigger
        LANGUAGE plpgsql AS
        $$
        BEGIN
            IF OLD.pv_snapshot IS NOT NULL
               AND (NEW.pv_snapshot IS DISTINCT FROM OLD.pv_snapshot) THEN
                RAISE EXCEPTION
                    'committee_sessions.pv_snapshot est immutable après scellement. '
                    'Aucune modification autorisée (INV-W05). session_id=%', OLD.id;
            END IF;
            RETURN NEW;
        END;
        $$
    """)

    op.execute(
        "DROP TRIGGER IF EXISTS trg_pv_snapshot_immutable ON committee_sessions"
    )
    op.execute("""
        CREATE TRIGGER trg_pv_snapshot_immutable
        BEFORE UPDATE ON committee_sessions
        FOR EACH ROW
        EXECUTE FUNCTION trg_fn_pv_snapshot_immutable()
    """)

    # ------------------------------------------------------------------
    # TRIGGER 2 — assessment_history append-only (INV-S03 étendu)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_fn_assessment_history_append_only()
        RETURNS trigger
        LANGUAGE plpgsql AS
        $$
        BEGIN
            RAISE EXCEPTION
                'assessment_history est append-only. '
                'Modification interdite (INV-S03).';
        END;
        $$
    """)

    op.execute(
        "DROP TRIGGER IF EXISTS trg_assessment_history_append_only ON assessment_history"
    )
    op.execute("""
        CREATE TRIGGER trg_assessment_history_append_only
        BEFORE UPDATE OR DELETE ON assessment_history
        FOR EACH ROW
        EXECUTE FUNCTION trg_fn_assessment_history_append_only()
    """)


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_assessment_history_append_only ON assessment_history"
    )
    op.execute("DROP FUNCTION IF EXISTS trg_fn_assessment_history_append_only()")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_pv_snapshot_immutable ON committee_sessions"
    )
    op.execute("DROP FUNCTION IF EXISTS trg_fn_pv_snapshot_immutable()")
