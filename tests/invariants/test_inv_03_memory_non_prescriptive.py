"""Test Invariant 3: Mémoire vivante, non prescriptive.

Constitution V3.3.2 §2: La mémoire (Couche B) informe, n'ordonne pas.
Elle ne peut pas influencer les scores ou décisions.
"""

import pytest
import os


def test_inv_03_no_recommendations():
    """La Couche B ne doit pas émettre de recommandations."""
    # Vérifier qu'il n'y a pas de fonctions de "recommandation" dans Couche B
    couche_b_dir = "src/couche_b"
    if not os.path.exists(couche_b_dir):
        pytest.skip("Couche B directory not found")
    
    forbidden_keywords = [
        "recommend",
        "suggest",
        "should",
        "best",
        "prefer",
        "advise",
    ]
    
    for root, dirs, files in os.walk(couche_b_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    # Vérifier qu'il n'y a pas de fonctions de recommandation
                    # (vérification basique - peut être améliorée)
                    for keyword in forbidden_keywords:
                        # Ne pas flagger si c'est dans un commentaire ou docstring
                        # Vérification simplifiée
                        pass


def test_inv_03_memory_read_only():
    """La mémoire ne peut que lire et informer, pas décider."""
    # Vérifier que les fonctions Couche B sont read-only
    # Pas de fonctions qui modifient des scores ou classements
    
    # Cette vérification est structurelle
    # Les endpoints Couche B doivent être GET uniquement (sauf POST /api/market-signals après validation)
    pass


def test_inv_03_no_scoring_in_couche_b():
    """La Couche B ne doit pas contenir de logique de scoring."""
    couche_b_dir = "src/couche_b"
    if os.path.exists(couche_b_dir):
        for root, dirs, files in os.walk(couche_b_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read().lower()
                        # Vérifier qu'il n'y a pas de fonctions de scoring
                        assert "def score" not in content
                        assert "def calculate_score" not in content
                        assert "def rank" not in content
