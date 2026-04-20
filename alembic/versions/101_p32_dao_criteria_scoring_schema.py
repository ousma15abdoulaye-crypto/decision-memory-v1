"""101 — P3.2 dao_criteria + process_workspaces scoring schema

Revision ID: 101_p32_dao_criteria_scoring_schema
Revises: 100_process_workspaces_zip_r2
Create Date: 2026-04-18

P3.2 Scoring Engine Article 15 — Migration schéma
Corpus canonique : CASE-28b05d85 (50/40/10 capacity/commercial/sustainability)

Upgrade idempotent (IF NOT EXISTS / contrainte gardée) : aligné sur 100_process_workspaces_zip_r2 —
évite DuplicateColumn quand ``alembic_version`` est rejoué sans DROP des colonnes (CI / tests).

Opérations upgrade (ordre strict CTO) :
- dao_criteria : +family, +weight_within_family, +criterion_mode, +scoring_mode, +min_threshold
- process_workspaces : +technical_qualification_threshold
- backfills : family ← criterion_category, weight_within_family ← ponderation, scoring_mode ← m16_scoring_mode
- cleanup : DROP min_weight_pct (probe COUNT IS NOT NULL = 0)

Réf. : MANDAT_P3.2_SCORING_ENGINE_PILOTE_V2 Article 15
"""

from alembic import op

revision = '101_p32_dao_criteria_scoring_schema'
down_revision = 'e7df16ec18ee'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """P3.2 upgrade — 10 opérations strictes."""

    # ========================================================================
    # 1. ADD COLUMN dao_criteria.family TEXT
    # ========================================================================
    # Famille critère P3.2 : TECHNICAL / COMMERCIAL / SUSTAINABILITY
    # Backfill depuis criterion_category (probe canonique CASE-28b05d85)

    op.execute("""
        ALTER TABLE dao_criteria
        ADD COLUMN IF NOT EXISTS family TEXT;
    """)

    # Backfill family depuis criterion_category
    # Mapping canonique probe CASE-28b05d85 : capacity→TECHNICAL, commercial→COMMERCIAL, sustainability→SUSTAINABILITY
    # DOCTRINE MÉTIER : 'essential' = critères GATE (checks), HORS famille scoring → family = NULL
    op.execute("""
        UPDATE dao_criteria
        SET family = CASE
            WHEN criterion_category = 'capacity' THEN 'TECHNICAL'
            WHEN criterion_category = 'commercial' THEN 'COMMERCIAL'
            WHEN criterion_category = 'sustainability' THEN 'SUSTAINABILITY'
            ELSE NULL
        END
        WHERE criterion_category IS NOT NULL;
    """)

    op.execute("""
        COMMENT ON COLUMN dao_criteria.family IS
        'Famille critère P3.2 : TECHNICAL / COMMERCIAL / SUSTAINABILITY (3 familles scoring uniquement).
        Backfill depuis criterion_category (capacity→TECHNICAL, commercial→COMMERCIAL, sustainability→SUSTAINABILITY).
        criterion_category=essential → family=NULL (critères GATE/checks, hors agrégat pondéré).
        Invariant 50/40/10 : somme weight_within_family par famille = 50% / 40% / 10%.';
    """)

    # ========================================================================
    # 2. ADD COLUMN dao_criteria.weight_within_family INTEGER
    # ========================================================================
    # Pondération intra-famille (%) : somme par famille = 100%
    # Backfill depuis ponderation (conversion globale → intra-famille)

    op.execute("""
        ALTER TABLE dao_criteria
        ADD COLUMN IF NOT EXISTS weight_within_family INTEGER;
    """)

    # Backfill weight_within_family = (ponderation / SUM_famille) × 100
    # Corpus actif uniquement (status NOT IN ('cancelled'))
    op.execute("""
        WITH family_sums AS (
            SELECT
                dc.workspace_id,
                dc.family,
                SUM(dc.ponderation) AS sum_famille
            FROM dao_criteria dc
            JOIN process_workspaces pw ON dc.workspace_id = pw.id
            WHERE dc.family IS NOT NULL
              AND dc.ponderation IS NOT NULL
              AND pw.status NOT IN ('cancelled')
            GROUP BY dc.workspace_id, dc.family
        )
        UPDATE dao_criteria dc
        SET weight_within_family = ROUND((dc.ponderation / fs.sum_famille) * 100.0)::INTEGER
        FROM family_sums fs
        WHERE dc.workspace_id = fs.workspace_id
          AND dc.family = fs.family
          AND dc.ponderation IS NOT NULL
          AND fs.sum_famille > 0;
    """)

    op.execute("""
        COMMENT ON COLUMN dao_criteria.weight_within_family IS
        'Pondération critère au sein de sa famille (%), INTEGER.
        Somme par famille = 100% (avant arrondi, dérive ≤ N critères).
        Backfill P3.2 : (ponderation / SUM_famille) × 100, corpus actif uniquement.
        Consommé par ScoringCore pour calcul score famille.';
    """)

    # ========================================================================
    # 3. ADD COLUMN dao_criteria.criterion_mode TEXT DEFAULT 'SCORE'
    # ========================================================================
    # Mode critère : SCORE (évaluation notée) / GATE (éliminatoire binaire)
    # Backfill GATE pour criterion_category = 'essential' (doctrine métier CTO)

    op.execute("""
        ALTER TABLE dao_criteria
        ADD COLUMN IF NOT EXISTS criterion_mode TEXT NOT NULL DEFAULT 'SCORE';
    """)

    # Backfill criterion_mode = 'GATE' pour critères essentiels
    # Doctrine métier : essentiels = checks/gates, ouvrent l'analyse, hors famille scoring
    op.execute("""
        UPDATE dao_criteria
        SET criterion_mode = 'GATE'
        WHERE criterion_category = 'essential';
    """)

    op.execute("""
        COMMENT ON COLUMN dao_criteria.criterion_mode IS
        'Mode critère P3.2 : SCORE (évaluation notée, contribue score famille) / GATE (éliminatoire binaire, vendor disqualifié si FAIL).
        Défaut SCORE. GATE consommé par ScoringCore gate checks.';
    """)

    # ========================================================================
    # 4. ADD COLUMN dao_criteria.scoring_mode TEXT
    # ========================================================================
    # Mode de scoring : RUBRIC / PRO_RATA / COUNT_BASED / BINARY / DETERMINISTIC
    # Backfill depuis m16_scoring_mode (probe confirme existence)

    op.execute("""
        ALTER TABLE dao_criteria
        ADD COLUMN IF NOT EXISTS scoring_mode TEXT;
    """)

    # Backfill scoring_mode depuis m16_scoring_mode
    # Probe 2 confirme : m16_scoring_mode existe
    op.execute("""
        UPDATE dao_criteria
        SET scoring_mode = UPPER(m16_scoring_mode)
        WHERE m16_scoring_mode IS NOT NULL;
    """)

    op.execute("""
        COMMENT ON COLUMN dao_criteria.scoring_mode IS
        'Mode de scoring P3.2 : RUBRIC / PRO_RATA / COUNT_BASED / BINARY / DETERMINISTIC.
        Backfill depuis m16_scoring_mode (uppercase). Consommé par ScoringCore pour calcul score critère.
        NULL accepté (mode non défini, scoring par défaut).';
    """)

    # Contrainte CHECK scoring_mode (valeurs autorisées P3.2)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'check_scoring_mode_p32'
            ) THEN
                ALTER TABLE dao_criteria
                ADD CONSTRAINT check_scoring_mode_p32 CHECK (
                    scoring_mode IS NULL OR scoring_mode IN (
                        'RUBRIC', 'PRO_RATA', 'COUNT_BASED', 'BINARY', 'DETERMINISTIC',
                        'NUMERIC', 'QUALITATIVE', 'NOT_APPLICABLE'
                    )
                );
            END IF;
        END $$;
    """)

    # ========================================================================
    # 5. ADD COLUMN dao_criteria.min_threshold FLOAT
    # ========================================================================
    # Seuil minimum critère (%) : si score < seuil, critère FAIL

    op.execute("""
        ALTER TABLE dao_criteria
        ADD COLUMN IF NOT EXISTS min_threshold FLOAT;
    """)

    op.execute("""
        COMMENT ON COLUMN dao_criteria.min_threshold IS
        'Seuil minimum critère (%) : si score < seuil, critère échoue.
        Utilisé par ScoringCore gate checks (criterion_mode = GATE).
        NULL = pas de seuil (critère SCORE standard).';
    """)

    # ========================================================================
    # 6. ADD COLUMN process_workspaces.technical_qualification_threshold FLOAT
    # ========================================================================
    # Seuil qualification technique workspace : si score technique < seuil, vendor disqualifié

    op.execute("""
        ALTER TABLE process_workspaces
        ADD COLUMN IF NOT EXISTS technical_qualification_threshold FLOAT NOT NULL DEFAULT 50.0;
    """)

    op.execute("""
        COMMENT ON COLUMN process_workspaces.technical_qualification_threshold IS
        'Seuil qualification technique (%) : si score_technique < seuil, vendor disqualifié (Gate D P3.2).
        Défaut 50.0 (convention SCI §5.2). Granularité : 1 seuil par workspace (appliqué tous vendors).
        Consommé par ScoringCore après calcul score famille TECHNICAL.';
    """)

    # ========================================================================
    # 7. DROP COLUMN dao_criteria.min_weight_pct
    # ========================================================================
    # Colonne fantôme (probe 3 : COUNT IS NOT NULL = 0)
    # Aucun consommateur métier (CRUD-only legacy)

    op.execute("""
        ALTER TABLE dao_criteria
        DROP COLUMN IF EXISTS min_weight_pct;
    """)


def downgrade() -> None:
    """P3.2 downgrade — ordre inverse strict, symétrique."""

    # 7. RESTORE min_weight_pct (optionnel, colonne fantôme)
    op.execute("""
        ALTER TABLE dao_criteria
        ADD COLUMN IF NOT EXISTS min_weight_pct FLOAT;
    """)

    # 6. DROP technical_qualification_threshold
    op.execute("""
        ALTER TABLE process_workspaces
        DROP COLUMN IF EXISTS technical_qualification_threshold;
    """)

    # 5. DROP min_threshold
    op.execute("""
        ALTER TABLE dao_criteria
        DROP COLUMN IF EXISTS min_threshold;
    """)

    # 4. DROP scoring_mode + CHECK constraint
    op.execute("""
        ALTER TABLE dao_criteria
        DROP CONSTRAINT IF EXISTS check_scoring_mode_p32;
    """)

    op.execute("""
        ALTER TABLE dao_criteria
        DROP COLUMN IF EXISTS scoring_mode;
    """)

    # 3. DROP criterion_mode
    op.execute("""
        ALTER TABLE dao_criteria
        DROP COLUMN IF EXISTS criterion_mode;
    """)

    # 2. DROP weight_within_family
    op.execute("""
        ALTER TABLE dao_criteria
        DROP COLUMN IF EXISTS weight_within_family;
    """)

    # 1. DROP family
    op.execute("""
        ALTER TABLE dao_criteria
        DROP COLUMN IF EXISTS family;
    """)
