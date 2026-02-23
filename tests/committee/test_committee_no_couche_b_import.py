"""T1 — Frontière A/B: scan AST sur src/couche_a/committee/.

Aucun import Couche B ne doit exister dans le module comité.
"""

import ast
from pathlib import Path

COMMITTEE_DIR = Path(__file__).resolve().parents[2] / "src" / "couche_a" / "committee"

FORBIDDEN_PATTERNS = {
    "couche_b",
    "mercuriale",
    "market_signal",
    "decision_history",
    "supplier_history",
    "normalisation",
}


def _collect_imports(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


class TestCoucheABBoundaryCommittee:
    def test_no_couche_b_imports_in_committee_module(self):
        assert COMMITTEE_DIR.exists(), f"Dossier introuvable: {COMMITTEE_DIR}"
        violations: list[tuple[str, str]] = []

        for py_file in COMMITTEE_DIR.rglob("*.py"):
            for imp in _collect_imports(py_file):
                for forbidden in FORBIDDEN_PATTERNS:
                    if forbidden in imp.lower():
                        violations.append(
                            (str(py_file.relative_to(COMMITTEE_DIR)), imp)
                        )

        assert (
            violations == []
        ), "Violations Couche A/B dans src/couche_a/committee/:\n" + "\n".join(
            f"  {f}: import {i}" for f, i in violations
        )

    def test_committee_module_files_exist(self):
        required = [
            "__init__.py",
            "models.py",
            "service.py",
            "router.py",
            "snapshot.py",
        ]
        missing = [f for f in required if not (COMMITTEE_DIR / f).exists()]
        assert missing == [], f"Fichiers manquants: {missing}"
