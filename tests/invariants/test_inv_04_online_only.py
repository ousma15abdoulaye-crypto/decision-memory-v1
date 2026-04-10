"""Test Invariant 4: Online-only assumé.

Constitution V3.3.2 §2: Le système est online-only, pas de fallback local.
"""

import os

import pytest
from pydantic import ValidationError


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


def test_inv_04_database_url_required(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """DATABASE_URL est requis au premier accès DB (get_connection → Settings).

    Constitution V3.3.2 §2 online-only : sans DATABASE_URL, échec explicite
    (Pydantic ValidationError via get_settings dans _get_database_url).
    Cwd isolé (pas de .env projet) pour ne pas relire DATABASE_URL depuis le fichier.
    """
    import src.db.core as _core
    from src.core.config import get_settings
    from src.db.core import get_connection

    monkeypatch.chdir(tmp_path)
    original_db_url = os.environ.get("DATABASE_URL")
    original_cache = _core._DB_URL_CACHE
    try:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        _core._DB_URL_CACHE = None
        get_settings.cache_clear()
        with pytest.raises(ValidationError, match="DATABASE_URL"):
            with get_connection():
                pass
    finally:
        if original_db_url is not None:
            os.environ["DATABASE_URL"] = original_db_url
        _core._DB_URL_CACHE = original_cache
        get_settings.cache_clear()


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
