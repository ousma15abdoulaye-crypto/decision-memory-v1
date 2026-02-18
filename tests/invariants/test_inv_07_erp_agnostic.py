"""Test Invariant 7: ERP-agnostique & stack claire.

Constitution V3.3.2 §2: Le système ne doit pas être couplé à un ERP spécifique.
"""

import os

import pytest


def test_inv_07_no_erp_imports():
    """Le code ne doit pas importer de bibliothèques ERP spécifiques."""
    # Liste des bibliothèques ERP connues à éviter
    erp_libraries = [
        "sap",
        "oracle",
        "dynamics",
        "salesforce",
        "odoo",
        "erpnext",
    ]

    src_dir = "src"
    if os.path.exists(src_dir):
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read().lower()
                        for erp_lib in erp_libraries:
                            # Vérifier qu'il n'y a pas d'imports ERP
                            if f"import {erp_lib}" in content or f"from {erp_lib}" in content:
                                pytest.fail(f"Import ERP détecté dans {filepath}: {erp_lib}")


def test_inv_07_stack_clear():
    """La stack doit être claire et documentée."""
    # Vérifier que requirements.txt existe et liste les dépendances
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", encoding="utf-8") as f:
            requirements = f.read()
            # Vérifier que les dépendances principales sont présentes
            assert "fastapi" in requirements.lower()
            assert "postgresql" in requirements.lower() or "psycopg" in requirements.lower()
    else:
        pytest.fail("requirements.txt manquant")


def test_inv_07_no_external_api_dependencies():
    """Le système ne doit pas dépendre d'APIs ERP externes."""
    # Vérifier qu'il n'y a pas de clients HTTP vers des APIs ERP
    src_dir = "src"
    erp_domains = [
        "sap.com",
        "oracle.com",
        "dynamics.microsoft.com",
        "salesforce.com",
    ]

    if os.path.exists(src_dir):
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                        for domain in erp_domains:
                            if domain in content:
                                pytest.fail(f"Référence à domaine ERP détectée dans {filepath}: {domain}")
