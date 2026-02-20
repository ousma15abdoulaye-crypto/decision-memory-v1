"""
Test : Frontière Couche A / Couche B (analyse statique AST)
Gate : 🔴 BLOQUANT CI (actif dès M-SCORING-ENGINE.done)
ADR  : ADR-0002 §2.4
REF  : §7 Constitution V3.3.2
"""

import ast
from pathlib import Path

import pytest

# Modules Couche B — interdits dans Couche A
COUCHE_B_MODULES = [
    "market_signal",
    "couche_b",
    "market_survey",
    "mercuriale",
    "decision_history",
    "context_panel",
    "dict_fuzzy",
]

# Chemins Couche A — où la violation est interdite
COUCHE_A_PATHS = [
    "src/scoring",
    "src/normalisation",
    "src/criteria",
    "src/extraction",
    "src/pipeline",
    "src/committee",
    "src/generation",
]


@pytest.mark.skip(
    reason="Actif dès M-SCORING-ENGINE.done (ADR-0002 §2.4). "
    "Retirer le skip quand M-SCORING-ENGINE est implémenté. "
    "Ce test analyse les imports Python statiquement (AST) "
    "et bloque CI si un module Couche B est importé dans Couche A."
)
def test_no_couche_b_import_in_couche_a():
    """
    §7 Constitution : La Couche B est strictement read-only
    vis-à-vis de la Couche A.
    Vérifié par analyse statique AST — pas de runtime.
    🔴 BLOQUE CI quand actif.
    """
    violations = []

    for couche_a_path in COUCHE_A_PATHS:
        path = Path(couche_a_path)
        if not path.exists():
            continue
        for py_file in path.rglob("*.py"):
            with open(py_file, encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read())
                except SyntaxError:
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import | ast.ImportFrom):
                    module = getattr(node, "module", "") or ""
                    names = [alias.name for alias in getattr(node, "names", [])]
                    all_names = [module] + names

                    for forbidden in COUCHE_B_MODULES:
                        for name in all_names:
                            if forbidden in name.lower():
                                violations.append(
                                    {
                                        "file": str(py_file),
                                        "line": node.lineno,
                                        "import": name,
                                        "forbidden": forbidden,
                                    }
                                )

    assert not violations, (
        f"VIOLATION §7 — {len(violations)} import(s) Couche B "
        f"dans Couche A :\n"
        + "\n".join(
            f"  {v['file']}:{v['line']} "
            f"→ '{v['import']}' (interdit: '{v['forbidden']}')"
            for v in violations
        )
    )
