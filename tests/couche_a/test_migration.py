from __future__ import annotations

from importlib import util
from pathlib import Path

from sqlalchemy import inspect

from src.couche_a import models


def _load_migration() -> object:
    migration_path = (
        Path(__file__).resolve().parents[2] / "alembic" / "versions" / "002_add_couche_a.py"
    )
    spec = util.spec_from_file_location("migration_002_add_couche_a", migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Migration introuvable.")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_downgrade(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "couche_a.sqlite3"
    monkeypatch.setenv("COUCHE_A_DB_PATH", str(db_path))
    monkeypatch.delenv("COUCHE_A_DB_URL", raising=False)
    models.reset_engine()
    engine = models.get_engine()

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
    assert "cases" not in tables
