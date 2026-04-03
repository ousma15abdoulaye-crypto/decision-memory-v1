"""
Tests for migration 060 — market_coverage auto-refresh trigger.

Verifies the trigger function and trigger exist in the migration DDL,
and that the downgrade is reversible.
"""

from __future__ import annotations

import ast
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "060_market_coverage_auto_refresh.py"
)


class TestMigration060:
    def test_migration_file_exists(self) -> None:
        assert MIGRATION_PATH.exists(), f"Missing: {MIGRATION_PATH}"

    def test_revision_chain(self) -> None:
        source = MIGRATION_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assigns = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in ("revision", "down_revision")
        }
        assert assigns["revision"] == "060_market_coverage_auto_refresh"
        assert assigns["down_revision"] == "059_m14_score_history_elimination_log"

    def test_creates_trigger_function(self) -> None:
        source = MIGRATION_PATH.read_text(encoding="utf-8")
        assert "fn_refresh_market_coverage" in source
        assert "REFRESH MATERIALIZED VIEW CONCURRENTLY" in source

    def test_targets_market_signals_v2(self) -> None:
        source = MIGRATION_PATH.read_text(encoding="utf-8")
        assert "market_signals_v2" in source
        assert "market_signals " not in source.replace("market_signals_v2", "")

    def test_trigger_is_for_each_statement(self) -> None:
        source = MIGRATION_PATH.read_text(encoding="utf-8")
        assert "FOR EACH STATEMENT" in source

    def test_exception_does_not_block_insert(self) -> None:
        source = MIGRATION_PATH.read_text(encoding="utf-8")
        assert "EXCEPTION WHEN OTHERS THEN" in source
        assert "RAISE WARNING" in source

    def test_downgrade_drops_trigger_and_function(self) -> None:
        source = MIGRATION_PATH.read_text(encoding="utf-8")
        assert "DROP TRIGGER IF EXISTS trg_refresh_market_coverage" in source
        assert "DROP FUNCTION IF EXISTS fn_refresh_market_coverage" in source
