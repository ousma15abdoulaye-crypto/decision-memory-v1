"""
Test : import statique Couche B dans Couche A (AST).
ADR  : ADR-0002 §2.4 · Constitution §7

Périmètre : `src/couche_a/**/*.py` — uniquement les nœuds `import` / `import from`.
Les appels dynamiques (`importlib.import_module`) ne sont pas vus par cet AST
(voir ADR-0009 / price_check).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_COUCHE_A_ROOT = Path("src/couche_a")

_COUCHE_B_TOKENS = (
    "couche_b",
    "src.couche_b",
)

# Modules autorisés explicitement (vide = aucune exception).
_ALLOWLIST_FILES: frozenset[str] = frozenset()


def _scan_file(py_file: Path) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        pytest.fail(f"{py_file.as_posix()}: syntaxe Python invalide — {exc}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name or ""
                for tok in _COUCHE_B_TOKENS:
                    if tok in name:
                        violations.append((node.lineno, name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for tok in _COUCHE_B_TOKENS:
                if tok in module:
                    violations.append((node.lineno, module))
            for alias in node.names:
                n = alias.name or ""
                for tok in _COUCHE_B_TOKENS:
                    if tok in n:
                        violations.append((node.lineno, n))
    return violations


def test_scoring_module_has_no_couche_b_dependency():
    """Aucun import statique vers Couche B sous src/couche_a/."""
    if not _COUCHE_A_ROOT.is_dir():
        pytest.skip("src/couche_a absent")

    all_violations: list[str] = []
    for py_file in _COUCHE_A_ROOT.rglob("*.py"):
        rel = py_file.as_posix()
        if rel in _ALLOWLIST_FILES:
            continue
        for lineno, name in _scan_file(py_file):
            all_violations.append(f"  {rel}:{lineno} → {name!r}")

    assert not all_violations, "Import Couche B détecté dans Couche A :\n" + "\n".join(
        all_violations
    )
