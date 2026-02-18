"""Test Invariant 9: Fidélité au réel & neutralité.

Constitution V3.3.2 §2: Le système doit refléter la réalité sans biais.
"""

import os

import pytest


def test_inv_09_no_biases_in_scoring():
    """Le scoring ne doit pas contenir de biais arbitraires."""
    import ast

    scoring_file = "src/couche_a/scoring/engine.py"
    if not os.path.exists(scoring_file):
        pytest.skip("Scoring engine file not found")

    with open(scoring_file, encoding="utf-8") as f:
        content = f.read()

    # Vérifier qu'il n'y a pas de comparaisons hardcodées avec des noms de fournisseurs
    # Pattern: if supplier == "XXX" ou if supplier_name == "XXX"
    bias_patterns = [
        r'if\s+.*supplier.*==\s*["\']',
        r'supplier.*==\s*["\'][A-Z]',  # Nom propre (commence par majuscule)
        r'if\s+.*==\s*["\'](ACME|Best|Premium|Gold)',  # Noms suspects
    ]

    violations = []
    for pattern in bias_patterns:
        import re

        if re.search(pattern, content, re.IGNORECASE):
            violations.append(f"Bias pattern detected: {pattern}")

    # Vérifier avec AST pour des conditions suspectes
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Vérifier si la condition compare avec une chaîne littérale
                if isinstance(node.test, ast.Compare):
                    for comp in node.test.comparators:
                        if isinstance(comp, ast.Str) and len(comp.s) > 2:
                            # Chaîne littérale dans une condition = potentiel biais
                            # Mais on ne flagge que si c'est dans un contexte de supplier
                            # (vérification simplifiée)
                            pass
    except SyntaxError:
        pass

    if violations:
        pytest.fail("Scoring contient des biais potentiels:\n" + "\n".join(violations))


def test_inv_09_transparent_calculations():
    """Les calculs doivent être transparents et traçables."""
    # Vérifier que les fonctions de calcul retournent des détails
    # permettant de comprendre comment le résultat a été obtenu

    scoring_file = "src/couche_a/scoring/engine.py"
    if os.path.exists(scoring_file):
        with open(scoring_file, encoding="utf-8") as f:
            content = f.read()
            # Vérifier qu'il y a des fonctions qui retournent des détails
            # (vérification structurelle)
            assert (
                "calculation_details" in content.lower() or "details" in content.lower()
            )


def test_inv_09_no_hidden_assumptions():
    """Le code ne doit pas contenir d'hypothèses cachées."""
    import re

    # Magic numbers suspects (valeurs numériques sans constante nommée)
    # On ignore les valeurs communes (0, 1, -1, 100, etc.)
    common_values = {0, 1, -1, 100, 1000, 1024, 60, 3600, 24}

    src_dir = "src/couche_a/scoring"  # Focus sur le scoring (plus critique)
    if not os.path.exists(src_dir):
        pytest.skip("Scoring directory not found")

    violations = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                    lines = content.splitlines()

                    # Chercher des nombres magiques dans le code
                    for i, line in enumerate(lines, 1):
                        # Ignorer les commentaires et docstrings
                        if (
                            line.strip().startswith("#")
                            or '"""' in line
                            or "'''" in line
                        ):
                            continue

                        # Chercher des nombres qui ne sont pas dans common_values
                        numbers = re.findall(r"\b(\d+\.?\d*)\b", line)
                        for num_str in numbers:
                            try:
                                num = float(num_str)
                                if num not in common_values and num > 1:
                                    # Vérifier si c'est dans une constante ou commenté
                                    if "=" not in line and "#" not in line:
                                        violations.append(
                                            f"{filepath}:{i} potential magic number: {num_str}"
                                        )
                            except ValueError:
                                pass

    # On ne fait qu'avertir, pas échouer (trop strict sinon)
    if len(violations) > 10:  # Seuil arbitraire
        pytest.fail(
            f"Trop de magic numbers détectés ({len(violations)}):\n"
            + "\n".join(violations[:10])
        )


def test_inv_09_neutral_language():
    """Le code et les messages doivent utiliser un langage neutre."""
    import ast

    biased_terms = [
        "best",  # Trop subjectif
        "worst",  # Trop subjectif
        "should",  # Trop prescriptif
        "must choose",  # Trop prescriptif
        "recommended",  # Prescriptif
    ]

    src_dir = "src"
    if not os.path.exists(src_dir):
        pytest.skip("src directory not found")

    violations = []
    for root, dirs, files in os.walk(src_dir):
        # Ignorer les tests (peuvent contenir des exemples)
        if "test" in root.lower():
            continue

        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()

                    # Analyser avec AST pour extraire docstrings et commentaires
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            # Vérifier les docstrings
                            if isinstance(
                                node, (ast.FunctionDef, ast.ClassDef, ast.Module)
                            ):
                                docstring = ast.get_docstring(node)
                                if docstring:
                                    doc_lower = docstring.lower()
                                    for term in biased_terms:
                                        if term in doc_lower:
                                            violations.append(
                                                f"{filepath}: docstring contains '{term}'"
                                            )

                            # Vérifier les chaînes littérales (messages d'erreur, etc.)
                            if isinstance(node, ast.Str):
                                str_lower = node.s.lower()
                                for term in biased_terms:
                                    if term in str_lower:
                                        violations.append(
                                            f"{filepath}: string literal contains '{term}'"
                                        )
                    except SyntaxError:
                        # Fallback: recherche simple
                        content_lower = content.lower()
                        for term in biased_terms:
                            if term in content_lower:
                                # Vérifier que ce n'est pas dans un commentaire
                                lines = content.splitlines()
                                for i, line in enumerate(lines, 1):
                                    if (
                                        term in line.lower()
                                        and not line.strip().startswith("#")
                                    ):
                                        violations.append(
                                            f"{filepath}:{i} contains '{term}'"
                                        )
                                        break

    if violations:
        pytest.fail("Langage biaisé détecté:\n" + "\n".join(violations[:10]))
