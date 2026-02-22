"""
test_no_evaluation_import_in_couche_a.py -- ADR-0010 D3
Gate CI : src/couche_a/ n'importe jamais src.evaluation.*
Scan AST mecanique -- bloquant CI.
"""

import ast
from pathlib import Path

import pytest

COUCHE_A_DIR = Path("src/couche_a")
FORBIDDEN_PATTERNS = [
    "src.evaluation",
    "evaluation.profiles",
    "evaluation",
]


def _collect_imports(filepath: Path) -> list[str]:
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def test_no_evaluation_import_in_couche_a():
    """
    ADR-0010 D3 -- Bloquant CI
    Aucun fichier src/couche_a/**/*.py n'importe src.evaluation.
    evaluation/profiles.py = seed-source migrations uniquement.
    """
    if not COUCHE_A_DIR.exists():
        pytest.skip("src/couche_a/ absent")

    violations = []
    for py_file in COUCHE_A_DIR.rglob("*.py"):
        for imp in _collect_imports(py_file):
            for forbidden in FORBIDDEN_PATTERNS:
                if imp == forbidden or imp.startswith(forbidden + "."):
                    violations.append(
                        f"{py_file.relative_to('.')} importe '{imp}'"
                        f" -- ADR-0010 D3 violation"
                    )

    assert (
        not violations
    ), f"ADR-0010 D3 viole -- {len(violations)} import(s) evaluation:\n" + "\n".join(
        f"  STOP {v}" for v in violations
    )


def test_evaluation_profiles_not_imported_in_price_check():
    """
    Verification ciblee : price_check/engine.py specifiquement.
    Source unique seuils prix = scoring_configs DB (ADR-0009 D2).
    """
    engine_file = Path("src/couche_a/price_check/engine.py")
    if not engine_file.exists():
        pytest.skip("price_check/engine.py absent")

    imports = _collect_imports(engine_file)
    for imp in imports:
        assert "evaluation" not in imp, (
            f"price_check/engine.py importe '{imp}' "
            f"-- violation ADR-0009 D2 + ADR-0010 D3"
        )
