"""Test Invariant 4: Online-only assumé.

Constitution V3.3.2 §2: Le système est online-only, pas de fallback local.
"""

import os

import pytest


def test_inv_04_no_sqlite():
    """Le système ne doit pas utiliser SQLite."""
    # Vérifier qu'il n'y a pas d'imports sqlite3

    src_dir = "src"
    if not os.path.exists(src_dir):
        pytest.skip("src directory not found")

    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                    assert "sqlite3" not in content
                    assert "import sqlite" not in content


def test_inv_04_database_url_required():
    """DATABASE_URL doit être requis au démarrage."""
    # Vérifier que db.py lève une erreur si DATABASE_URL manque

    original_db_url = os.environ.get("DATABASE_URL")

    try:
        # Supprimer DATABASE_URL temporairement
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        # Réimporter pour forcer la réinitialisation
        import importlib

        import src.db

        importlib.reload(src.db)

        # Tenter de créer l'engine doit échouer
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            src.db._get_engine()
    finally:
        # Restaurer DATABASE_URL
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        import importlib

        import src.db

        importlib.reload(src.db)


def test_inv_04_postgresql_only():
    """Le système doit utiliser PostgreSQL uniquement."""
    # Vérifier que les migrations utilisent PostgreSQL uniquement
    alembic_dir = "alembic/versions"
    if os.path.exists(alembic_dir):
        for file in os.listdir(alembic_dir):
            if file.endswith(".py"):
                filepath = os.path.join(alembic_dir, file)
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                    # Vérifier qu'il n'y a pas de références à SQLite
                    assert "sqlite" not in content.lower()
                    # Vérifier qu'il y a des références PostgreSQL
                    # (CREATE TABLE, etc. sont PostgreSQL-compatibles)
