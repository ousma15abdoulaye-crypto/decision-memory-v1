"""
m5_pre_vendors_consolidation

Consolide vendor_identities → vendors.
Supprime la table vendors legacy (résiduelle · était vide).

Contexte :
  Table vendors legacy (4 colonnes · hors Alembic) coexistait avec
  vendor_identities (référentiel canonique M4 · 34 colonnes).
  Probe 2026-03-03 :
    - vendors legacy        : 0 lignes non-null dans market_signals.vendor_id
    - vendor_identities     : 0 lignes local · 661 prod (wave 1 + 2)
    - FK market_signals     : vendor_id existe en colonne mais aucune FK formelle
    - Décision CTO          : VERDICT A — consolidation autorisée

Note sur l'idempotence :
  La migration est idempotente dans les deux sens :
  - upgrade  : si vendor_identities absente → consolidation déjà faite → RAISE NOTICE + skip
  - downgrade : si vendors absente → déjà annulé → RAISE NOTICE + skip
  Chaque étape vérifie l'état réel avant d'agir.
  Aucune commande ne retente un rename déjà fait.

Noms contraintes/index confirmés probe SQL D + E (2026-03-03) :
  Contraintes pré-consolidation (sur vendor_identities) :
    vendor_identities_pkey · vendor_identities_fingerprint_key
    vendor_identities_vendor_id_key · vendor_identities_vcrn_key
    uq_vi_canonical_name
  Contraintes post-consolidation (sur vendors) :
    vendors_pkey · vendors_fingerprint_key
    vendors_vendor_id_key · vendors_vcrn_key
    uq_vendors_canonical_name
  Index pré  : idx_vi_canonical · idx_vi_verification
  Index post : idx_vendors_canonical · idx_vendors_verification

Révision     : m5_pre_vendors_consolidation
Down revision: m4_patch_a_fix
Closes       : TD-004 · TD-009
"""

from alembic import op

revision = "m5_pre_vendors_consolidation"
down_revision = "m4_patch_a_fix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        DECLARE
            v_count INTEGER;
        BEGIN
            -- ── Garde idempotence ──────────────────────────────────────────
            -- Si vendor_identities absente → consolidation déjà appliquée → skip propre.
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name   = 'vendor_identities'
            ) THEN
                RAISE NOTICE
                    'm5_pre_vendors_consolidation : '
                    'vendor_identities absente — consolidation déjà appliquée — skip';
                RETURN;
            END IF;

            -- ── Étape 1 : DROP vendors legacy si présente et vide ─────────
            -- Si vendors n'existe pas (ex. après downgrade), on saute le DROP.
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name   = 'vendors'
            ) THEN
                SELECT COUNT(*) INTO v_count FROM vendors;
                IF v_count > 0 THEN
                    RAISE EXCEPTION
                        'm5_pre_vendors_consolidation : '
                        'vendors legacy contient % ligne(s) non triviales — '
                        'DROP refusé — arbitrage CTO requis',
                        v_count;
                END IF;
                DROP TABLE vendors;
            END IF;

            -- ── Étape 2 : RENAME vendor_identities → vendors ──────────────
            ALTER TABLE vendor_identities RENAME TO vendors;

            -- ── Étape 3 : RENAME PK (si ancien nom encore présent) ────────
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema     = 'public'
                  AND table_name       = 'vendors'
                  AND constraint_name  = 'vendor_identities_pkey'
            ) THEN
                ALTER TABLE vendors RENAME CONSTRAINT
                    vendor_identities_pkey TO vendors_pkey;
            END IF;

            -- ── Étape 4 : RENAME contraintes UNIQUE (si anciens noms) ─────
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema    = 'public'
                  AND table_name      = 'vendors'
                  AND constraint_name = 'vendor_identities_fingerprint_key'
            ) THEN
                ALTER TABLE vendors RENAME CONSTRAINT
                    vendor_identities_fingerprint_key TO vendors_fingerprint_key;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema    = 'public'
                  AND table_name      = 'vendors'
                  AND constraint_name = 'vendor_identities_vendor_id_key'
            ) THEN
                ALTER TABLE vendors RENAME CONSTRAINT
                    vendor_identities_vendor_id_key TO vendors_vendor_id_key;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema    = 'public'
                  AND table_name      = 'vendors'
                  AND constraint_name = 'vendor_identities_vcrn_key'
            ) THEN
                ALTER TABLE vendors RENAME CONSTRAINT
                    vendor_identities_vcrn_key TO vendors_vcrn_key;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema    = 'public'
                  AND table_name      = 'vendors'
                  AND constraint_name = 'uq_vi_canonical_name'
            ) THEN
                ALTER TABLE vendors RENAME CONSTRAINT
                    uq_vi_canonical_name TO uq_vendors_canonical_name;
            END IF;

            -- ── Étape 5 : RENAME index non-contraintes (si anciens noms) ──
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename  = 'vendors'
                  AND indexname  = 'idx_vi_canonical'
            ) THEN
                ALTER INDEX idx_vi_canonical RENAME TO idx_vendors_canonical;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename  = 'vendors'
                  AND indexname  = 'idx_vi_verification'
            ) THEN
                ALTER INDEX idx_vi_verification RENAME TO idx_vendors_verification;
            END IF;

        END $$;
    """)


def downgrade() -> None:
    """
    Downgrade NON SYMÉTRIQUE — documenté honnêtement.

    Restitue le rename vendors ← vendor_identities.
    La table vendors legacy originale (4 colonnes) n'est pas recréée.
    Les données prod (661 lignes en prod) survivent sous vendor_identities.
    Pour rollback complet : restaurer depuis backup Railway.
    """
    op.execute("""
        DO $$
        BEGIN
            -- ── Garde idempotence ──────────────────────────────────────────
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name   = 'vendors'
            ) THEN
                RAISE NOTICE
                    'm5_pre_vendors_consolidation downgrade : '
                    'vendors absente — skip';
                RETURN;
            END IF;

            -- ── Étape 1 : RENAME index non-contraintes ────────────────────
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename  = 'vendors'
                  AND indexname  = 'idx_vendors_canonical'
            ) THEN
                ALTER INDEX idx_vendors_canonical RENAME TO idx_vi_canonical;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename  = 'vendors'
                  AND indexname  = 'idx_vendors_verification'
            ) THEN
                ALTER INDEX idx_vendors_verification RENAME TO idx_vi_verification;
            END IF;

            -- ── Étape 2 : RENAME contraintes UNIQUE ───────────────────────
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema    = 'public'
                  AND table_name      = 'vendors'
                  AND constraint_name = 'uq_vendors_canonical_name'
            ) THEN
                ALTER TABLE vendors RENAME CONSTRAINT
                    uq_vendors_canonical_name TO uq_vi_canonical_name;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema    = 'public'
                  AND table_name      = 'vendors'
                  AND constraint_name = 'vendors_vcrn_key'
            ) THEN
                ALTER TABLE vendors RENAME CONSTRAINT
                    vendors_vcrn_key TO vendor_identities_vcrn_key;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema    = 'public'
                  AND table_name      = 'vendors'
                  AND constraint_name = 'vendors_vendor_id_key'
            ) THEN
                ALTER TABLE vendors RENAME CONSTRAINT
                    vendors_vendor_id_key TO vendor_identities_vendor_id_key;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema    = 'public'
                  AND table_name      = 'vendors'
                  AND constraint_name = 'vendors_fingerprint_key'
            ) THEN
                ALTER TABLE vendors RENAME CONSTRAINT
                    vendors_fingerprint_key TO vendor_identities_fingerprint_key;
            END IF;

            -- ── Étape 3 : RENAME PK ───────────────────────────────────────
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema    = 'public'
                  AND table_name      = 'vendors'
                  AND constraint_name = 'vendors_pkey'
            ) THEN
                ALTER TABLE vendors RENAME CONSTRAINT
                    vendors_pkey TO vendor_identities_pkey;
            END IF;

            -- ── Étape 4 : RENAME vendors → vendor_identities ──────────────
            ALTER TABLE vendors RENAME TO vendor_identities;

        END $$;
    """)
