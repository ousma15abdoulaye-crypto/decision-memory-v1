"""L12 — AST gate anti-Couche-B (Pipeline A).

ADR-0011 — frontière Couche A/B.
Aucun fichier de src/couche_a/pipeline/ ne doit importer Couche B.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PIPELINE_DIR = Path("src/couche_a/pipeline")
FORBIDDEN = [
    "couche_b",
    "market_signal",
    "mercuriale",
    "decision_history",
    "supplier_history",
]


def _imports_from_file(fp: Path) -> list[str]:
    tree = ast.parse(fp.read_text(encoding="utf-8"))
    result: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.append(node.module)
    return result


def test_no_couche_b_import_in_pipeline():
    """
    ADR-0011 — frontière Couche A/B.
    Aucun fichier de src/couche_a/pipeline/ ne doit importer Couche B.
    """
    if not PIPELINE_DIR.exists():
        pytest.skip("src/couche_a/pipeline/ absent — milestone non commencé")

    violations: list[tuple[str, str]] = []

    for py_file in PIPELINE_DIR.rglob("*.py"):
        for imp in _imports_from_file(py_file):
            for forbidden in FORBIDDEN:
                if imp == forbidden or imp.startswith(forbidden + "."):
                    violations.append((str(py_file), imp))

    assert not violations, (
        "Imports Couche B interdits détectés dans Pipeline A: " f"{violations}"
    )
