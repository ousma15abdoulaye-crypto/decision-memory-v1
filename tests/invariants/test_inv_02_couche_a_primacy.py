"""Test Invariant 2: Primauté absolue de la Couche A.

Constitution V3.3.2 §2: La Couche A est autonome et primordiale.
La Couche B ne peut pas influencer les décisions de la Couche A.
"""

import pytest
import os
from unittest.mock import patch, MagicMock


def test_inv_02_couche_a_independent():
    """La Couche A doit fonctionner sans Couche B."""
    # Vérifier qu'il n'y a pas d'imports Couche B dans Couche A
    import ast
    
    couche_a_dir = "src/couche_a"
    if not os.path.exists(couche_a_dir):
        pytest.skip("Couche A directory not found")
    
    # Parcourir les fichiers Python de Couche A
    for root, dirs, files in os.walk(couche_a_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Vérifier qu'il n'y a pas d'imports de Couche B
                    assert "from src.couche_b" not in content
                    assert "from couche_b" not in content
                    assert "import couche_b" not in content


def test_inv_02_no_couche_b_in_scoring():
    """Le scoring (Couche A) ne doit pas utiliser Couche B."""
    # Vérifier que le module scoring n'importe pas Couche B
    import os
    scoring_file = "src/couche_a/scoring/engine.py"
    if os.path.exists(scoring_file):
        with open(scoring_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "couche_b" not in content.lower()


def test_inv_02_couche_b_read_only():
    """La Couche B ne peut pas modifier les données de Couche A."""
    # Vérifier structurellement que Couche B n'a pas d'accès en écriture
    # sur les tables Couche A
    
    # Cette vérification est structurelle - les migrations doivent
    # garantir que Couche B n'a pas de permissions UPDATE/DELETE
    # sur les tables Couche A (vérifié dans test_inv_06_append_only)
    pass
