"""
Correctifs post-PATCH-A · failles Copilot · 3 points migration.

Revision ID: m4_patch_a_fix
Revises: m4_patch_a_vendor_structure_v410
Create Date: 2026-03-02

TABLE CIBLE : vendor_identities
  Scénario 1 confirmé probe 2026-03-02.
  vendor_identities = référentiel canonique · 34 colonnes · 102 vendors prod.
  vendors = legacy 4 colonnes · hors scope.

FAILLES CORRIGÉES ICI :
  F1 · ADD CONSTRAINT UNIQUE non idempotente
       → garde pg_constraint avant ADD
       → contrainte : uq_vi_canonical_name (nom confirmé probe)

  F2 · RENAME COLUMN last_verified_at → verified_at non conditionnel
       → garde information_schema double-sens
       → échoue proprement si état incohérent

  F3 · Garde doublon vérifiait name_normalized seul
       → faux positif sur fournisseurs multi-régions (même nom · 2 régions)
       → canonical_name = name_normalized|region_code (confirmé probe)
       → garde corrigée : vérifie canonical_name directement

FAILLES CORRIGÉES HORS MIGRATION :
  F4 · dry-run faux                  → etl_vendors_wave2.py
  F5 · connexion parasite dry-run    → etl_vendors_wave2.py
  F6 · docstring _process_row fausse → etl_vendors_wave2.py
  F7 · commentaire pg_trgm inexact   → ce fichier + TD-002
  F8 · alembic head contradictoire   → HANDOVER_M4_TRANSMISSION.md
  F9 · TD-002 "activer pg_trgm" faux → TECHNICAL_DEBT.md

NOTE pg_trgm (F7) :
  pg_trgm est DÉJÀ activée via 005_add_couche_b.
  Hors scope ici = index GIN sur canonical_name + match_vendor_by_name().
  L'extension elle-même n'est pas à recréer.
"""

from alembic import op

revision = "m4_patch_a_fix"
down_revision = "m4_patch_a_vendor_structure_v410"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── Garde entrée ─────────────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'vendor_identities'
            ) THEN
                RAISE EXCEPTION
                    'vendor_identities introuvable · '
                    'probe scénario 1 invalide · '
                    'arrêt migration';
            END IF;
        END $$;
    """)

    # ── F1 · UNIQUE(canonical_name) idempotente ───────────────
    #
    # ADD CONSTRAINT IF NOT EXISTS n'existe pas en PostgreSQL.
    # La garde pg_constraint est le pattern correct pour idempotence.
    # En prod : uq_vi_canonical_name existe déjà (PATCH-A). Rien à faire.
    # En env vierge : la contrainte est créée proprement.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname  = 'uq_vi_canonical_name'
                  AND conrelid = 'vendor_identities'::regclass
                  AND contype  = 'u'
            ) THEN
                ALTER TABLE vendor_identities
                ADD CONSTRAINT uq_vi_canonical_name
                UNIQUE (canonical_name);
            END IF;
        END $$;
    """)

    # ── F2 · RENAME COLUMN conditionnel ──────────────────────
    #
    # En prod : verified_at existe · last_verified_at absente (PATCH-A OK).
    # Sur rerun : rien à faire.
    # Si état incohérent : exception explicite et lisible.
    op.execute("""
        DO $$
        DECLARE
            has_old BOOLEAN;
            has_new BOOLEAN;
        BEGIN
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name  = 'vendor_identities'
                  AND column_name = 'last_verified_at'
            ) INTO has_old;

            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name  = 'vendor_identities'
                  AND column_name = 'verified_at'
            ) INTO has_new;

            IF has_old AND NOT has_new THEN
                ALTER TABLE vendor_identities
                RENAME COLUMN last_verified_at TO verified_at;

            ELSIF NOT has_old AND has_new THEN
                NULL;  -- Déjà renommé · rerun safe

            ELSIF has_old AND has_new THEN
                RAISE EXCEPTION
                    'État incohérent : last_verified_at ET verified_at '
                    'coexistent dans vendor_identities · '
                    'résolution manuelle requise';

            ELSE
                RAISE EXCEPTION
                    'État incohérent : ni last_verified_at ni verified_at '
                    'dans vendor_identities · '
                    'résolution manuelle requise';
            END IF;
        END $$;
    """)

    # ── F3 · Garde doublon canonical_name (clé correcte) ─────
    #
    # FAILLE version précédente : GROUP BY name_normalized
    # → faux positif : "traore sarl" à BKO + MPT = 2 canonical distincts
    #   ("traore sarl|BKO" · "traore sarl|MPT") · ATTENDU · pas un doublon.
    #
    # Correction : GROUP BY canonical_name directement.
    # canonical_name = name_normalized|region_code (probe confirmé).
    # Un vrai doublon = même vendor_id + même région = même canonical.
    op.execute("""
        DO $$
        DECLARE
            v_count  INTEGER;
            v_exemples TEXT;
        BEGIN
            SELECT
                COUNT(*),
                string_agg(canonical_name, ' · ' ORDER BY canonical_name)
            INTO v_count, v_exemples
            FROM (
                SELECT canonical_name
                FROM vendor_identities
                GROUP BY canonical_name
                HAVING COUNT(*) > 1
                LIMIT 10
            ) t;

            IF v_count > 0 THEN
                RAISE EXCEPTION
                    'Doublons canonical_name détectés (%) : [%] · '
                    'UNIQUE(canonical_name) impossible · '
                    'résolution CTO requise avant migration',
                    v_count, v_exemples;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Ce fix renforce m4_patch_a_vendor_structure_v410.
    # Downgrade = retour à m4_patch_a_vendor_structure_v410.
    # La contrainte et le rename vivent dans cette migration parent.
    # Rien à défaire ici.
    pass
