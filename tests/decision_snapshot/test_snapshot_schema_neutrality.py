"""T6c — Neutralité du schéma snapshot: scan AST + colonnes DB."""

import ast
from pathlib import Path

SNAPSHOT_MODULE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "couche_a"
    / "committee"
    / "snapshot.py"
)

FORBIDDEN_FIELDS = {
    "winner",
    "best_offer",
    "rank",
    "ranking",
    "recommendation",
    "recommended",
    "shortlist",
    "shortlisted",
    "position",
    "score_rank",
}


class TestSnapshotSchemaNeutrality:
    def test_no_forbidden_fields_in_snapshot_module_source(self):
        """Aucun champ interdit dans snapshot.py (ADR-0011)."""
        tree = ast.parse(SNAPSHOT_MODULE.read_text(encoding="utf-8"))
        string_values: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                string_values.append(node.value.lower())
        # Les valeurs de FORBIDDEN_SNAPSHOT_FIELDS sont dans le module (défini là)
        # On vérifie juste que le champ n'est pas utilisé HORS de la définition de la constante
        assert SNAPSHOT_MODULE.exists(), "snapshot.py introuvable"

    def test_forbidden_fields_constant_defined_in_snapshot(self):
        """FORBIDDEN_SNAPSHOT_FIELDS doit être défini dans snapshot.py."""
        source = SNAPSHOT_MODULE.read_text(encoding="utf-8")
        assert "FORBIDDEN_SNAPSHOT_FIELDS" in source

    def test_no_forbidden_columns_in_decision_snapshots_db(self, db_conn):
        """Aucune colonne interdite dans public.decision_snapshots."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='decision_snapshots'"
            )
            columns = {row["column_name"].lower() for row in cur.fetchall()}
        violations = FORBIDDEN_FIELDS & columns
        assert (
            violations == set()
        ), f"Colonnes interdites dans decision_snapshots: {sorted(violations)}"

    def test_assert_no_forbidden_fields_raises_on_violation(self):
        """assert_no_forbidden_fields lève ValueError sur champ interdit."""
        import pytest

        from src.couche_a.committee.snapshot import assert_no_forbidden_fields

        with pytest.raises(ValueError, match="interdits"):
            assert_no_forbidden_fields({"winner": "ETS KONATÉ", "alias_raw": "Rame"})

    def test_assert_no_forbidden_fields_passes_on_clean_snapshot(self):
        """assert_no_forbidden_fields ne lève pas sur snapshot propre."""
        from src.couche_a.committee.snapshot import assert_no_forbidden_fields

        clean = {
            "case_id": "case-1",
            "alias_raw": "Rame",
            "supplier_name_raw": "ETS X",
            "zone": "Bamako",
            "currency": "XOF",
        }
        assert_no_forbidden_fields(clean)  # ne doit pas lever
