"""v52_p1_002 — Auto-historisation assessments (P1.2).

Revision ID: v52_p1_002_assessment_auto_history
Revises: v52_p1_001_immutability_triggers
Branch labels: None
Depends on: None

ÉTAPE A — Évolution de assessment_history :
  - changed_by  : INTEGER NOT NULL → DROP NOT NULL (trigger insert avec NULL)
  - change_reason : TEXT NOT NULL  → DROP NOT NULL (valeur auto depuis trigger)
  - Colonnes ajoutées (safe DO $$ pattern) :
      assessment_id     UUID NULL FK criterion_assessments — alias de criterion_assessment_id
      old_score         NUMERIC(7,2) NULL — extrait de cell_json (best-effort)
      new_score         NUMERIC(7,2) NULL
      old_confidence    NUMERIC(4,3) NULL
      new_confidence    NUMERIC(4,3) NULL
      reason            TEXT NULL — alias lisible de change_reason
      changed_by_uuid   UUID NULL — user_id UUID depuis session variable app.current_user

ÉTAPE B — Trigger auto-historisation :
  - Table    : criterion_assessments
  - Moment   : AFTER UPDATE
  - Condition: WHEN (OLD.confidence IS DISTINCT FROM NEW.confidence
                     OR OLD.cell_json IS DISTINCT FROM NEW.cell_json)
  - Action   : INSERT INTO assessment_history (full audit row)

NOTE ARCHITECTURE :
  criterion_assessments n'a PAS de colonne "score" — le score est dans
  cell_json (JSONB). Le trigger extrait cell_json->>'score' en best-effort
  (NULL si absent ou non-castable). La colonne confidence NUMERIC(3,2)
  est tracée directement.

  app.current_user est posé par src/db/core.py via set_config() — voir
  le correctif associé dans ce même commit (3 lignes dans get_connection).

REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "v52_p1_002_assessment_auto_history"
down_revision = "v52_p1_001_immutability_triggers"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # ÉTAPE A — Adapter le schéma de assessment_history
    # -----------------------------------------------------------------------

    # A1 — Rendre changed_by nullable (INTEGER existant — on garde le type,
    #       les lignes insérées par trigger auront changed_by = NULL)
    op.execute("ALTER TABLE assessment_history ALTER COLUMN changed_by DROP NOT NULL")

    # A2 — Rendre change_reason nullable (trigger fournit sa propre valeur)
    op.execute(
        "ALTER TABLE assessment_history ALTER COLUMN change_reason DROP NOT NULL"
    )

    # A3 — Colonnes additionnelles (safe : EXCEPTION WHEN duplicate_column)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE assessment_history
                ADD COLUMN assessment_id UUID
                REFERENCES criterion_assessments(id) ON DELETE CASCADE;
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            ALTER TABLE assessment_history ADD COLUMN old_score NUMERIC(7,2);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            ALTER TABLE assessment_history ADD COLUMN new_score NUMERIC(7,2);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            ALTER TABLE assessment_history ADD COLUMN old_confidence NUMERIC(4,3);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            ALTER TABLE assessment_history ADD COLUMN new_confidence NUMERIC(4,3);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            ALTER TABLE assessment_history
                ADD COLUMN reason TEXT DEFAULT 'Modification directe';
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            ALTER TABLE assessment_history ADD COLUMN changed_by_uuid UUID;
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$
    """)

    # -----------------------------------------------------------------------
    # ÉTAPE B — Trigger d'auto-historisation sur criterion_assessments
    # -----------------------------------------------------------------------

    op.execute("""
        CREATE OR REPLACE FUNCTION trg_fn_assessment_auto_history()
        RETURNS trigger
        LANGUAGE plpgsql AS
        $$
        DECLARE
            v_user_uuid     UUID;
            v_reason        TEXT;
            v_old_score     NUMERIC(7,2);
            v_new_score     NUMERIC(7,2);
        BEGIN
            -- Capture user UUID depuis variable de session (app.current_user)
            -- posée par src/db/core.py via set_config().
            -- Si absente ou non-castable → NULL (pas d'erreur).
            BEGIN
                IF current_setting('app.current_user', true) IS NOT NULL
                   AND current_setting('app.current_user', true) != ''
                THEN
                    v_user_uuid := current_setting('app.current_user', true)::uuid;
                END IF;
            EXCEPTION WHEN invalid_text_representation THEN
                v_user_uuid := NULL;
            END;

            -- Raison de modification depuis variable de session ou valeur par défaut
            v_reason := COALESCE(
                NULLIF(current_setting('app.change_reason', true), ''),
                'Modification directe'
            );

            -- Score : extrait de cell_json (best-effort, NULL si absent)
            -- criterion_assessments n'a pas de colonne score dédiée.
            BEGIN
                v_old_score := (OLD.cell_json->>'score')::NUMERIC;
            EXCEPTION WHEN OTHERS THEN
                v_old_score := NULL;
            END;
            BEGIN
                v_new_score := (NEW.cell_json->>'score')::NUMERIC;
            EXCEPTION WHEN OTHERS THEN
                v_new_score := NULL;
            END;

            INSERT INTO assessment_history (
                id,
                tenant_id,
                criterion_assessment_id,
                assessment_id,
                workspace_id,
                old_score,
                new_score,
                old_confidence,
                new_confidence,
                changed_by,
                changed_by_uuid,
                change_reason,
                reason,
                change_metadata,
                created_at
            ) VALUES (
                gen_random_uuid(),
                NEW.tenant_id,
                NEW.id,
                NEW.id,
                NEW.workspace_id,
                v_old_score,
                v_new_score,
                OLD.confidence,
                NEW.confidence,
                NULL,
                v_user_uuid,
                v_reason,
                v_reason,
                jsonb_build_object(
                    'trigger',       true,
                    'old_cell_json', OLD.cell_json,
                    'new_cell_json', NEW.cell_json
                ),
                NOW()
            );

            RETURN NEW;
        END;
        $$
    """)

    op.execute(
        "DROP TRIGGER IF EXISTS trg_assessment_auto_history ON criterion_assessments"
    )
    op.execute("""
        CREATE TRIGGER trg_assessment_auto_history
        AFTER UPDATE ON criterion_assessments
        FOR EACH ROW
        WHEN (
            OLD.confidence IS DISTINCT FROM NEW.confidence
            OR OLD.cell_json IS DISTINCT FROM NEW.cell_json
        )
        EXECUTE FUNCTION trg_fn_assessment_auto_history()
    """)


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    # B — Supprimer trigger + fonction
    op.execute(
        "DROP TRIGGER IF EXISTS trg_assessment_auto_history ON criterion_assessments"
    )
    op.execute("DROP FUNCTION IF EXISTS trg_fn_assessment_auto_history()")

    # A — Supprimer colonnes ajoutées (les NOT NULL supprimés ne sont pas restaurés :
    #     des lignes trigger avec NULL changed_by peuvent exister)
    for col in (
        "changed_by_uuid",
        "reason",
        "new_confidence",
        "old_confidence",
        "new_score",
        "old_score",
        "assessment_id",
    ):
        op.execute(f"ALTER TABLE assessment_history DROP COLUMN IF EXISTS {col}")
