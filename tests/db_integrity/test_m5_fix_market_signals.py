"""
Tests M5-FIX — market_signals.vendor_id INTEGER → UUID
RÈGLE-07 : Zéro ... · assertions explicites
RÈGLE-17 : 1 test minimum par invariant de migration

Architecture fixtures :
  - db_conn      : connexion autocommit=True · lecture schéma uniquement
  - db_transaction : cursor autocommit=False · rollback auto · INSERT/DELETE

FK non testée en local :
  La table market_signals est protégée append-only (REVOKE UPDATE +
  SELECT FOR KEY SHARE bloqué). Toute FK depuis market_signals vers
  vendors déclenche InsufficientPrivilege lors des DELETE vendors.
  La contrainte logique est documentée dans ADR-M5-FIX-001.
  La FK est appliquée en prod via scripts/apply_fk_prod.py.
"""

import uuid

import pytest


class TestMigrationM5Fix:
    """Invariants post-migration m5_fix_market_signals_vendor_type.
    Chaque test = 1 invariant nommé.
    """

    def test_vendor_id_type_est_uuid(self, db_conn):
        """
        Invariant principal : vendor_id doit être UUID après migration.
        Échoue si ALTER COLUMN n'a pas été appliqué.
        """
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT data_type, udt_name
                FROM information_schema.columns
                WHERE table_name  = 'market_signals'
                  AND column_name = 'vendor_id'
            """)
            row = cur.fetchone()

        assert row is not None, "Colonne vendor_id absente de market_signals"
        assert row["udt_name"] == "uuid", (
            f"vendor_id type attendu : uuid · " f"type réel : {row['udt_name']}"
        )

    def test_vendor_id_nullable(self, db_conn):
        """
        vendor_id doit rester nullable.
        Un market_signal peut exister sans vendor associé.
        """
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_name  = 'market_signals'
                  AND column_name = 'vendor_id'
            """)
            row = cur.fetchone()

        assert row is not None
        assert row["is_nullable"] == "YES", (
            "vendor_id doit être nullable — "
            "un signal marché peut ne pas avoir de vendor"
        )

    def test_index_vendor_id_existe(self, db_conn):
        """Index sur vendor_id doit exister pour les jointures M9.
        Nom réel confirmé probe P4 : idx_signals_vendor.
        """
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'market_signals'
                  AND indexname = 'idx_signals_vendor'
            """)
            row = cur.fetchone()

        assert row is not None, "Index idx_signals_vendor absent"

    def test_insert_valid_vendor_id_uuid(self, db_transaction):
        """
        INSERT avec vendor_id UUID valide doit réussir.
        Utilise le schéma réel de market_signals (table legacy 005_add_couche_b).
        Colonnes NOT NULL : observed_at · created_at.
        Colonnes signal_quality · formula_version · data_points
        n'existent pas encore (créées en M9).
        Rollback automatique via db_transaction — pas d'effet de bord.
        """
        vendor_id = str(uuid.uuid4())

        db_transaction.execute(
            """
            INSERT INTO vendors (
                id, canonical_name, name_raw, name_normalized,
                region_code, fingerprint, vendor_id
            ) VALUES (
                %s::uuid, 'test_vendor_m5fix', 'Test Vendor M5Fix',
                'test vendor m5fix', 'BKO',
                md5(random()::text), 'DMS-VND-BKO-9997-Z'
            )
        """,
            (vendor_id,),
        )

        db_transaction.execute(
            """
            INSERT INTO market_signals (
                vendor_id,
                observed_at,
                created_at
            ) VALUES (
                %s::uuid,
                now()::text,
                now()::text
            )
        """,
            (vendor_id,),
        )

        db_transaction.execute(
            """
            SELECT COUNT(*) AS c FROM market_signals
            WHERE vendor_id = %s::uuid
        """,
            (vendor_id,),
        )
        row = db_transaction.fetchone()
        assert row["c"] == 1, "INSERT market_signal avec vendor_id UUID a échoué"

    def test_insert_vendor_id_integer_refuse(self, db_transaction):
        """
        INSERT avec valeur INTEGER brute doit échouer.
        Prouve que le type UUID est enforced par PostgreSQL.
        """
        with pytest.raises(Exception):
            db_transaction.execute("""
                INSERT INTO market_signals (
                    vendor_id,
                    observed_at,
                    created_at
                ) VALUES (
                    42,
                    now()::text,
                    now()::text
                )
            """)


class TestGardesUpgrade:
    """Documente l'invariant pré-migration : table vide obligatoire."""

    def test_market_signals_vide_avant_migration(self, db_conn):
        """
        market_signals doit être vide avant M5-FIX.
        Si ce test échoue après migration : données insérées post-upgrade.
        Avant migration : arbitrage CTO obligatoire si COUNT > 0.
        Ne pas forcer la migration.
        """
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM market_signals")
            row = cur.fetchone()

        assert row["c"] == 0, (
            f"market_signals contient {row['c']} ligne(s). "
            "Vérifier que les tests précédents ont bien rollbacké. "
            "En production : arbitrage CTO requis."
        )
