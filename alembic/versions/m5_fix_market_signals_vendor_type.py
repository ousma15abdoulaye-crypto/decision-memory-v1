"""
m5_fix_market_signals_vendor_type

Corrige le type de market_signals.vendor_id : INTEGER → UUID.

Contexte :
  005_add_couche_b.py a créé vendor_id en INTEGER avec FK vers vendors(id).
  M5-PRE a supprimé la FK lors du DROP de vendors legacy.
  Cette migration restaure la cohérence de type UUID.

FK non recréée dans cette migration :
  La table market_signals est protégée append-only (REVOKE UPDATE +
  SELECT FOR KEY SHARE bloqué). Toute FK depuis market_signals vers
  vendors déclenche FOR KEY SHARE lors des DELETE vendors, incompatible
  avec cette protection dans l'environnement local.
  La contrainte logique est documentée dans ADR-M5-FIX-001.
  La FK sera appliquée manuellement en prod via scripts/apply_fk_prod.py.

Idempotence :
  Si vendor_id est déjà UUID → skip propre sans erreur.

Prérequis :
  market_signals doit être vide (COUNT = 0) si vendor_id encore INTEGER.

Downgrade :
  Restitue INTEGER. Bloqué si vendor_id contient des valeurs non NULL.
  Rollback complet : restaurer depuis backup Railway.

Révision     : m5_fix_market_signals_vendor_type
Down revision: m5_pre_vendors_consolidation
"""

revision = "m5_fix_market_signals_vendor_type"
down_revision = "m5_pre_vendors_consolidation"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:

    # ── Garde 0 : idempotence — déjà appliquée → skip ────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name  = 'market_signals'
                  AND column_name = 'vendor_id'
                  AND udt_name    = 'uuid'
            ) THEN
                RAISE NOTICE
                    'vendor_id déjà UUID — migration déjà appliquée — skip';
                RETURN;
            END IF;
        END $$;
    """)

    # ── Garde 1 : market_signals doit être vide ───────────────────────────
    op.execute("""
        DO $$
        DECLARE v_count BIGINT;
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name  = 'market_signals'
                  AND column_name = 'vendor_id'
                  AND udt_name    = 'uuid'
            ) THEN
                SELECT COUNT(*) INTO v_count FROM market_signals;
                IF v_count > 0 THEN
                    RAISE EXCEPTION
                        'market_signals contient % ligne(s). '
                        'ALTER TYPE sur données réelles interdit. '
                        'Arbitrage CTO obligatoire.',
                        v_count;
                END IF;
            END IF;
        END $$;
    """)

    # ── Garde 2 : vendor_id doit être INTEGER avant ALTER ─────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name  = 'market_signals'
                  AND column_name = 'vendor_id'
                  AND data_type   = 'integer'
            ) THEN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name  = 'market_signals'
                      AND column_name = 'vendor_id'
                      AND udt_name    = 'uuid'
                ) THEN
                    RAISE NOTICE
                        'vendor_id déjà UUID — skip ALTER';
                    RETURN;
                ELSE
                    RAISE EXCEPTION
                        'vendor_id absent ou type inattendu dans market_signals. '
                        'État inattendu — arbitrage CTO requis.';
                END IF;
            END IF;
        END $$;
    """)

    # ── Garde 3 : vendors.id doit être UUID ──────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name  = 'vendors'
                  AND column_name = 'id'
                  AND udt_name    = 'uuid'
            ) THEN
                RAISE EXCEPTION
                    'vendors.id absent ou non-UUID. '
                    'Consolidation M5-PRE incomplète — arbitrage CTO requis.';
            END IF;
        END $$;
    """)

    # ── Suppression index sur vendor_id si présent (idempotence) ─────────
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'market_signals'
                  AND indexname = 'idx_signals_vendor'
            ) THEN
                DROP INDEX idx_signals_vendor;
                RAISE NOTICE 'Index idx_signals_vendor supprimé';
            END IF;
        END $$;
    """)

    # ── ALTER COLUMN INTEGER → UUID ───────────────────────────────────────
    # Exécuté uniquement si vendor_id est encore INTEGER.
    # Table vide confirmée par Garde 1.
    # USING NULL : toutes les valeurs passent à NULL (table vide · sans perte).
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name  = 'market_signals'
                  AND column_name = 'vendor_id'
                  AND data_type   = 'integer'
            ) THEN
                EXECUTE 'ALTER TABLE market_signals
                         ALTER COLUMN vendor_id TYPE UUID USING NULL';
                RAISE NOTICE 'vendor_id : INTEGER → UUID appliqué';
            ELSE
                RAISE NOTICE 'vendor_id déjà UUID — ALTER skippé';
            END IF;
        END $$;
    """)

    # ── Recréation index sur vendor_id ───────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'market_signals'
                  AND indexname = 'idx_signals_vendor'
            ) THEN
                EXECUTE 'CREATE INDEX idx_signals_vendor
                         ON market_signals(vendor_id)';
                RAISE NOTICE 'Index idx_signals_vendor recréé';
            ELSE
                RAISE NOTICE 'Index idx_signals_vendor déjà présent — skip';
            END IF;
        END $$;
    """)

    # ── Note : FK non créée (voir docstring) ─────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE
                'market_signals.vendor_id : INTEGER → UUID. '
                'FK non créée : incompatible avec protection append-only locale. '
                'Voir ADR-M5-FIX-001 et scripts/apply_fk_prod.py.';
        END $$;
    """)


def downgrade() -> None:

    # ── Garde downgrade : bloqué si vendor_id non NULL ───────────────────
    op.execute("""
        DO $$
        DECLARE v_count BIGINT;
        BEGIN
            SELECT COUNT(*) INTO v_count
            FROM market_signals
            WHERE vendor_id IS NOT NULL;
            IF v_count > 0 THEN
                RAISE EXCEPTION
                    '% ligne(s) ont un vendor_id non NULL. '
                    'Downgrade UUID → INTEGER impossible sans perte. '
                    'Restaurer depuis backup Railway.',
                    v_count;
            END IF;
        END $$;
    """)

    # ── DROP FK si présente (appliquée manuellement via apply_fk_prod.py) ─
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE constraint_name = 'market_signals_vendor_id_fkey'
                  AND table_name      = 'market_signals'
            ) THEN
                ALTER TABLE market_signals
                    DROP CONSTRAINT market_signals_vendor_id_fkey;
                RAISE NOTICE 'FK market_signals_vendor_id_fkey supprimée';
            END IF;
        END $$;
    """)

    # ── DROP index ────────────────────────────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'market_signals'
                  AND indexname = 'idx_signals_vendor'
            ) THEN
                DROP INDEX idx_signals_vendor;
            END IF;
        END $$;
    """)

    # ── ALTER COLUMN UUID → INTEGER ───────────────────────────────────────
    op.execute("""
        ALTER TABLE market_signals
            ALTER COLUMN vendor_id TYPE INTEGER
            USING NULL;
    """)

    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE
                'DOWNGRADE : market_signals.vendor_id : UUID → INTEGER';
        END $$;
    """)
