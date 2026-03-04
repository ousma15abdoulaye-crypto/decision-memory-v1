"""
Tests M5 — invariants migration 040
RÈGLE-17 : 1 test par invariant · assertions explicites
"""

import pytest

from src.couche_b.mercuriale import repository as merc_repo


class TestMigration040:
    def test_mercuriale_sources_existe(self, db_conn):
        row = db_conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name   = 'mercuriale_sources'
            """).fetchone()
        assert row is not None, "Table mercuriale_sources absente"

    def test_mercurials_existe(self, db_conn):
        row = db_conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name   = 'mercurials'
            """).fetchone()
        assert row is not None, "Table mercurials absente"

    def test_sha256_unique(self, db_conn):
        row = db_conn.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name      = 'mercuriale_sources'
              AND constraint_type = 'UNIQUE'
              AND constraint_name = 'uq_mercuriale_sources_sha256'
            """).fetchone()
        assert row is not None, "Contrainte UNIQUE sha256 absente"

    def test_trois_colonnes_prix_presentes(self, db_conn):
        for col in ("price_min", "price_avg", "price_max", "unit_price"):
            row = db_conn.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name  = 'mercurials'
                  AND column_name = %s
                """,
                (col,),
            ).fetchone()
            assert row is not None, f"Colonne {col} absente"

    def test_pas_de_zone_id_dans_sources(self, db_conn):
        """mercuriale_sources n'a pas de zone_id : zone portée par chaque ligne."""
        row = db_conn.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name  = 'mercuriale_sources'
              AND column_name = 'zone_id'
            """).fetchone()
        assert row is None, "zone_id ne doit pas exister dans mercuriale_sources"

    def test_pas_fk_unit_id(self, db_conn):
        """unit_id sans FK vers units (résolu en M6)."""
        row = db_conn.execute("""
            SELECT tc.constraint_name
            FROM information_schema.table_constraints    AS tc
            JOIN information_schema.key_column_usage     AS kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name      = 'mercurials'
              AND tc.constraint_type = 'FOREIGN KEY'
              AND kcu.column_name    = 'unit_id'
            """).fetchone()
        assert row is None, "FK unit_id ne doit pas exister en M5"

    def test_pas_fk_item_id(self, db_conn):
        """item_id sans FK vers procurement_references (résolu en M6)."""
        row = db_conn.execute("""
            SELECT tc.constraint_name
            FROM information_schema.table_constraints    AS tc
            JOIN information_schema.key_column_usage     AS kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name      = 'mercurials'
              AND tc.constraint_type = 'FOREIGN KEY'
              AND kcu.column_name    = 'item_id'
            """).fetchone()
        assert row is None, "FK item_id ne doit pas exister en M5"

    def test_unit_price_colonne_normale(self, db_conn):
        """unit_price = colonne normale (pas GENERATED ALWAYS)."""
        row = db_conn.execute("""
            SELECT is_generated
            FROM information_schema.columns
            WHERE table_name  = 'mercurials'
              AND column_name = 'unit_price'
            """).fetchone()
        assert row is not None
        assert row["is_generated"] in (
            "NEVER",
            "NO",
            None,
        ), "unit_price ne doit pas être GENERATED ALWAYS"

    def test_insert_trois_prix_valides(self, db_conn):
        sha = "d" * 64
        # autocommit=True : pas de commit() explicite
        db_conn.execute(
            """
            INSERT INTO mercuriale_sources (filename, sha256, year, source_type)
            VALUES ('t.pdf', %s, 2024, 'official_dgmp')
            ON CONFLICT (sha256) DO NOTHING
            """,
            (sha,),
        )

        src = db_conn.execute(
            "SELECT id FROM mercuriale_sources WHERE sha256 = %s", (sha,)
        ).fetchone()

        db_conn.execute(
            """
            INSERT INTO mercurials (
                source_id, item_canonical,
                price_min, price_avg, price_max, unit_price, year
            ) VALUES (%s, 'Riz blanc 25kg TEST', 17000, 18500, 20000, 18500, 2024)
            """,
            (str(src["id"]),),
        )

        row = db_conn.execute(
            """
            SELECT price_min, price_avg, price_max, unit_price
            FROM mercurials WHERE item_canonical = 'Riz blanc 25kg TEST'
              AND source_id = %s
            """,
            (str(src["id"]),),
        ).fetchone()

        assert float(row["price_min"]) == 17000.0
        assert float(row["price_avg"]) == 18500.0
        assert float(row["price_max"]) == 20000.0
        assert (
            float(row["unit_price"]) == 18500.0
        ), "unit_price doit être égal à price_avg"

        # Cleanup explicite (autocommit — pas de rollback)
        db_conn.execute(
            "DELETE FROM mercurials WHERE source_id = %s", (str(src["id"]),)
        )
        db_conn.execute("DELETE FROM mercuriale_sources WHERE sha256 = %s", (sha,))

    def test_source_type_invalide_rejete(self, db_conn):
        with pytest.raises(Exception):
            db_conn.execute("""
                INSERT INTO mercuriale_sources
                    (filename, sha256, year, source_type)
                VALUES ('t.pdf', 'fakehash001', 2024, 'TYPE_INVALIDE')
                """)


class TestIdempotenceSHA256:
    def test_double_insert_sha256_skip(self, db_conn):
        sha = "e" * 64
        # autocommit=True : chaque INSERT est auto-commis
        for _ in range(2):
            db_conn.execute(
                """
                INSERT INTO mercuriale_sources
                    (filename, sha256, year, source_type)
                VALUES ('t.pdf', %s, 2024, 'official_dgmp')
                ON CONFLICT (sha256) DO NOTHING
                """,
                (sha,),
            )

        count = db_conn.execute(
            "SELECT COUNT(*) AS c FROM mercuriale_sources WHERE sha256 = %s",
            (sha,),
        ).fetchone()["c"]
        assert count == 1, "Doublon SHA256 inséré"

        # Cleanup explicite
        db_conn.execute("DELETE FROM mercuriale_sources WHERE sha256 = %s", (sha,))


class TestResolveZoneIdAlias:
    """BUG-001 : Badiangara (typo PDF) résout vers Bandiagara (geo_master)."""

    def test_badiangara_resolves_same_as_bandiagara(self):
        zone_bandiagara = merc_repo.resolve_zone_id("Bandiagara")
        zone_badiangara = merc_repo.resolve_zone_id("Badiangara")
        assert zone_bandiagara is not None, "Bandiagara doit exister dans geo_master"
        assert (
            zone_badiangara == zone_bandiagara
        ), "Badiangara (typo) doit résoudre la même zone que Bandiagara"
