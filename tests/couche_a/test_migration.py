from __future__ import annotations

import os
from importlib import util
from pathlib import Path

import pytest
from sqlalchemy import inspect


def _load_migration() -> object:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "002_add_couche_a.py"
    )
    spec = util.spec_from_file_location("migration_002_add_couche_a", migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Migration introuvable.")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_downgrade(db_engine) -> None:
    """Run migration upgrade/downgrade against PostgreSQL."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set – skipping PostgreSQL tests")
    engine = db_engine

    migration = _load_migration()
    migration.upgrade(engine)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "cases" in tables
    assert "offers" in tables
    assert "audits" in tables

    migration.downgrade(engine)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    # La table 'cases' doit être préservée
    assert "cases" in tables
    # Les autres tables de Couche A doivent être supprimées
    assert "offers" not in tables
    assert "audits" not in tables
    assert "lots" not in tables
    assert "documents" not in tables
    assert "extractions" not in tables
    assert "analyses" not in tables
