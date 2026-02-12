from __future__ import annotations

import os
from importlib import util
from pathlib import Path

import pytest
from sqlalchemy import inspect


def _load_migration() -> object:
    migration_path = (
        Path(__file__).resolve().parents[2] / "alembic" / "versions" / "003_add_procurement_extensions.py"
    )
    spec = util.spec_from_file_location("migration_003_procurement_extended", migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Migration 003 introuvable.")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_downgrade(db_engine) -> None:
    """Run migration 003 upgrade/downgrade against PostgreSQL."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set – skipping PostgreSQL tests")
    engine = db_engine

    migration = _load_migration()
    
    # Upgrade: créer les nouvelles tables
    migration.upgrade(engine)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    # Vérifier que les nouvelles tables sont créées
    assert "procurement_references" in tables
    assert "procurement_categories" in tables
    assert "procurement_thresholds" in tables
    
    # Vérifier que la table lots existe (devrait être dans 002)
    assert "lots" in tables
    
    # Vérifier les colonnes ajoutées à lots
    lots_columns = [col['name'] for col in inspector.get_columns('lots')]
    assert "category_id" in lots_columns
    
    # Vérifier les colonnes ajoutées à cases
    cases_columns = [col['name'] for col in inspector.get_columns('cases')]
    assert "ref_id" in cases_columns
    assert "category_id" in cases_columns
    assert "estimated_value" in cases_columns
    assert "closing_date" in cases_columns
    
    # Vérifier que les seed data sont insérées
    with engine.connect() as conn:
        # 6 catégories
        result = conn.execute(inspector.engine.text("SELECT COUNT(*) FROM procurement_categories"))
        count = result.scalar()
        assert count == 6, f"Expected 6 categories, got {count}"
        
        # 3 seuils
        result = conn.execute(inspector.engine.text("SELECT COUNT(*) FROM procurement_thresholds"))
        count = result.scalar()
        assert count == 3, f"Expected 3 thresholds, got {count}"
    
    # Downgrade: supprimer les tables et colonnes
    migration.downgrade(engine)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    # Les nouvelles tables doivent être supprimées
    assert "procurement_references" not in tables
    assert "procurement_categories" not in tables
    assert "procurement_thresholds" not in tables
    
    # Vérifier que les colonnes sont supprimées de lots
    lots_columns = [col['name'] for col in inspector.get_columns('lots')]
    assert "category_id" not in lots_columns
    
    # Vérifier que les colonnes sont supprimées de cases
    cases_columns = [col['name'] for col in inspector.get_columns('cases')]
    assert "ref_id" not in cases_columns
    assert "category_id" not in cases_columns
    assert "estimated_value" not in cases_columns
    assert "closing_date" not in cases_columns
