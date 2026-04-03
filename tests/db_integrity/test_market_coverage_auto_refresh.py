"""
Tests for migrations 060 and 067 — market_coverage auto-refresh trigger.

Migration 060 introduced ``fn_refresh_market_coverage`` with
``REFRESH MATERIALIZED VIEW CONCURRENTLY``, which cannot run inside a
transaction block (trigger context) and therefore always silently fails.

Migration 067 fixes this by replacing the function with a non-concurrent
refresh that actually executes within the trigger transaction.
"""

from __future__ import annotations

import ast
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"

MIGRATION_PATH = _MIGRATIONS / "060_market_coverage_auto_refresh.py"
MIGRATION_067_PATH = _MIGRATIONS / "067_fix_market_coverage_trigger.py"


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
        assert "REFRESH MATERIALIZED VIEW" in source

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


class TestMigration067:
    """Migration 067 replaces fn_refresh_market_coverage without CONCURRENTLY.

    ``REFRESH MATERIALIZED VIEW CONCURRENTLY`` cannot run inside a transaction
    block — trigger functions always execute within the INSERT transaction, so
    the original 060 implementation was a guaranteed no-op.  Migration 067
    fixes this with a plain (non-concurrent) refresh.
    """

    def test_migration_file_exists(self) -> None:
        assert MIGRATION_067_PATH.exists(), f"Missing: {MIGRATION_067_PATH}"

    def test_revision_chain(self) -> None:
        source = MIGRATION_067_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assigns = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in ("revision", "down_revision")
        }
        assert assigns["revision"] == "067_fix_market_coverage_trigger"
        assert assigns["down_revision"] == "066_bridge_triggers"

    def test_uses_non_concurrent_refresh(self) -> None:
        """Upgrade function must NOT use CONCURRENTLY — it runs inside a transaction."""
        source = MIGRATION_067_PATH.read_text(encoding="utf-8")
        assert "REFRESH MATERIALIZED VIEW" in source
        assert (
            "REFRESH MATERIALIZED VIEW CONCURRENTLY"
            not in source.split("def upgrade")[1].split("def downgrade")[0]
        )

    def test_still_catches_exceptions(self) -> None:
        source = MIGRATION_067_PATH.read_text(encoding="utf-8")
        assert "EXCEPTION WHEN OTHERS THEN" in source
        assert "RAISE WARNING" in source

    def test_replaces_same_function(self) -> None:
        source = MIGRATION_067_PATH.read_text(encoding="utf-8")
        assert "fn_refresh_market_coverage" in source
        assert "CREATE OR REPLACE FUNCTION" in source
