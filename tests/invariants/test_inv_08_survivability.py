"""Test Invariant 8: Survivabilité & lisibilité.

Constitution V3.3.2 §2: Le code doit être maintenable et survivre aux changements.
"""

import ast
import os

import pytest


def test_inv_08_code_readable():
    """Le code doit être lisible (pas de code obfusqué)."""
    # Vérifier que les fichiers Python sont valides syntaxiquement
    src_dir = "src"
    if os.path.exists(src_dir):
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, encoding="utf-8") as f:
                            content = f.read()
                            # Vérifier que le code est valide Python
                            ast.parse(content)
                    except SyntaxError as e:
                        pytest.fail(f"Erreur de syntaxe dans {filepath}: {e}")


def test_inv_08_documentation_present():
    """Les modules critiques doivent avoir de la documentation."""
    critical_modules = [
        "src/db.py",
        "src/auth.py",
        "src/couche_a/routers.py",
    ]

    for module_path in critical_modules:
        if os.path.exists(module_path):
            with open(module_path, encoding="utf-8") as f:
                content = f.read()
                # Vérifier qu'il y a au moins une docstring
                assert '"""' in content or "'''" in content, (
                    f"Module {module_path} sans docstring"
                )


def test_inv_08_migrations_versioned():
    """Les migrations doivent être versionnées et tracées."""
    alembic_dir = "alembic/versions"
    if os.path.exists(alembic_dir):
        migrations = [f for f in os.listdir(alembic_dir) if f.endswith(".py")]
        assert len(migrations) > 0, "Aucune migration trouvée"

        # Vérifier que chaque migration a un revision ID
        for migration_file in migrations:
            filepath = os.path.join(alembic_dir, migration_file)
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
                assert "revision = " in content, (
                    f"Migration {migration_file} sans revision ID"
                )


def test_inv_08_no_hardcoded_secrets():
    """Le code ne doit pas contenir de secrets en dur."""
    forbidden_patterns = [
        r"password\s*=\s*['\"][^'\"]+['\"]",
        r"secret\s*=\s*['\"][^'\"]+['\"]",
        r"api_key\s*=\s*['\"][^'\"]+['\"]",
    ]

    src_dir = "src"
    if os.path.exists(src_dir):
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                        for pattern in forbidden_patterns:
                            import re

                            if re.search(pattern, content, re.IGNORECASE):
                                # Ignorer les valeurs par défaut documentées comme non sécurisées
                                if "CHANGE_IN_PRODUCTION" not in content:
                                    pytest.fail(
                                        f"Secret potentiel détecté dans {filepath}"
                                    )
