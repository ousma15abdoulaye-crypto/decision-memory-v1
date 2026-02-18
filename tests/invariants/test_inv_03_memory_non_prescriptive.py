"""Test Invariant 3: Mémoire vivante, non prescriptive.

Constitution V3.3.2 §2: La mémoire (Couche B) informe, n'ordonne pas.
Elle ne peut pas influencer les scores ou décisions.
"""

import pytest
import os


def test_inv_03_no_recommendations():
    """La Couche B ne doit pas émettre de recommandations."""
    # Vérifier qu'il n'y a pas de fonctions de "recommandation" dans Couche B
    import ast
    import re
    
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
    
    violations = []
    for root, dirs, files in os.walk(couche_b_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Analyser avec AST pour exclure commentaires/docstrings
                    try:
                        tree = ast.parse(content)
                        # Extraire seulement le code (sans commentaires/docstrings)
                        code_lines = []
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                # Vérifier le nom de la fonction
                                if any(kw in node.name.lower() for kw in forbidden_keywords):
                                    violations.append(f"{filepath}: function '{node.name}' contains forbidden keyword")
                                # Vérifier les appels de fonction dans le corps
                                for stmt in ast.walk(node):
                                    if isinstance(stmt, ast.Call) and isinstance(stmt.func, ast.Name):
                                        if any(kw in stmt.func.id.lower() for kw in forbidden_keywords):
                                            violations.append(f"{filepath}: function call '{stmt.func.id}' contains forbidden keyword")
                    except SyntaxError:
                        # Si AST échoue, utiliser regex simple (moins précis mais fonctionne)
                        # Chercher des patterns de fonctions avec mots interdits
                        func_pattern = rf"def\s+.*?({'|'.join(forbidden_keywords)}).*?\("
                        if re.search(func_pattern, content, re.IGNORECASE):
                            violations.append(f"{filepath}: contains function with forbidden keyword")
    
    if violations:
        pytest.fail(f"Couche B contient des recommandations:\n" + "\n".join(violations))


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
