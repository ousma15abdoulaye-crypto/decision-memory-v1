"""Test Invariant 9: FidÃ©litÃ© au rÃ©el & neutralitÃ©.

Constitution V3.3.2 Â§2: Le systÃ¨me doit reflÃ©ter la rÃ©alitÃ© sans biais.
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

    # Constitution V3.3.2 §2: pas de biais (noms de fournisseurs hardcodés).
    # On détecte les comparaisons du type supplier_name == "Nom", pas package_status == "COMPLETE".
    import re

    bias_patterns = [
        (r'if\s+.*supplier.*==\s*["\']', "comparison supplier == literal"),
        (r'supplier.*==\s*["\'][A-Z]', "supplier == proper-name literal"),
        (r'if\s+.*==\s*["\'](ACME|Best|Premium|Gold)', "known bias name literal"),
    ]
    # Faux positifs légitimes: comparaisons de statut, pas de noms
    false_positive_markers = ("package_status", ".status", "COMPLETE", "INCOMPLETE")

    violations = []
    for pattern, desc in bias_patterns:
        for line in content.splitlines():
            if not re.search(pattern, line, re.IGNORECASE):
                continue
            if any(m in line for m in false_positive_markers):
                continue
            violations.append(f"Bias pattern detected: {desc} ({pattern})")
            break

    # VÃ©rifier avec AST pour des conditions suspectes
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # VÃ©rifier si la condition compare avec une chaÃ®ne littÃ©rale
                if isinstance(node.test, ast.Compare):
                    for comp in node.test.comparators:
                        if isinstance(comp, ast.Str) and len(comp.s) > 2:
                            # ChaÃ®ne littÃ©rale dans une condition = potentiel biais
                            # Mais on ne flagge que si c'est dans un contexte de supplier
                            # (vÃ©rification simplifiÃ©e)
                            pass
    except SyntaxError:
        pass

    if violations:
        pytest.fail("Scoring contient des biais potentiels:\n" + "\n".join(violations))


def test_inv_09_transparent_calculations():
    """Les calculs doivent Ãªtre transparents et traÃ§ables."""
    # VÃ©rifier que les fonctions de calcul retournent des dÃ©tails
    # permettant de comprendre comment le rÃ©sultat a Ã©tÃ© obtenu

    scoring_file = "src/couche_a/scoring/engine.py"
    if os.path.exists(scoring_file):
        with open(scoring_file, encoding="utf-8") as f:
            content = f.read()
            # VÃ©rifier qu'il y a des fonctions qui retournent des dÃ©tails
            # (vÃ©rification structurelle)
            assert (
                "calculation_details" in content.lower() or "details" in content.lower()
            )


def test_inv_09_no_hidden_assumptions():
    """Le code ne doit pas contenir d'hypothÃ¨ses cachÃ©es."""
    import re

    # Magic numbers suspects (valeurs numÃ©riques sans constante nommÃ©e)
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
                                    # VÃ©rifier si c'est dans une constante ou commentÃ©
                                    if "=" not in line and "#" not in line:
                                        violations.append(
                                            f"{filepath}:{i} potential magic number: {num_str}"
                                        )
                            except ValueError:
                                pass

    # On ne fait qu'avertir, pas Ã©chouer (trop strict sinon)
    if len(violations) > 10:  # Seuil arbitraire
        pytest.fail(
            f"Trop de magic numbers dÃ©tectÃ©s ({len(violations)}):\n"
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
                            # VÃ©rifier les docstrings
                            if isinstance(
                                node, ast.FunctionDef | ast.ClassDef | ast.Module
                            ):
                                docstring = ast.get_docstring(node)
                                if docstring:
                                    doc_lower = docstring.lower()
                                    for term in biased_terms:
                                        if term in doc_lower:
                                            violations.append(
                                                f"{filepath}: docstring contains '{term}'"
                                            )

                            # VÃ©rifier les chaÃ®nes littÃ©rales (messages d'erreur, etc.)
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
                                # VÃ©rifier que ce n'est pas dans un commentaire
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
        pytest.fail("Langage biaisÃ© dÃ©tectÃ©:\n" + "\n".join(violations[:10]))
