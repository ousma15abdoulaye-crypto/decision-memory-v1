"""
T-L11 : Gates AST — séparation moteur / pipeline / renderers.
3 tests AST — corps complets — INV-AS6/AS8/AS12/AS13.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ENGINE_DIR = Path("src/couche_a/analysis_summary/engine")


def _collect_imports(fp: Path) -> list[str]:
    """Collecte tous les imports d'un fichier Python."""
    tree = ast.parse(fp.read_text(encoding="utf-8"))
    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.append(node.module)
    return result


def _collect_text(fp: Path) -> str:
    """Contenu texte brut d'un fichier."""
    return fp.read_text(encoding="utf-8").lower()


def test_engine_does_not_import_pipeline_execution_functions():
    """
    INV-AS8 : aucun fichier engine/* n'importe les fonctions
    run_pipeline_a_partial ou run_pipeline_a_e2e.
    """
    if not ENGINE_DIR.exists():
        pytest.skip("engine/ absent — milestone non démarré")

    violations: list[str] = []
    forbidden_imports = [
        "run_pipeline_a_partial",
        "run_pipeline_a_e2e",
        "run_pipeline",
    ]
    forbidden_modules = [
        "couche_a.pipeline.service",
    ]

    for py_file in ENGINE_DIR.rglob("*.py"):
        text = _collect_text(py_file)
        for forbidden in forbidden_imports:
            if forbidden in text:
                violations.append(f"{py_file.relative_to('.')} contient '{forbidden}'")
        for imp in _collect_imports(py_file):
            for forbidden_mod in forbidden_modules:
                if imp == forbidden_mod or imp.startswith(forbidden_mod):
                    violations.append(f"{py_file.relative_to('.')} importe '{imp}'")

    assert not violations, (
        f"INV-AS8 violé — {len(violations)} violation(s) pipeline dans engine/ :\n"
        + "\n".join(f"  🛑 {v}" for v in violations)
    )


def test_engine_has_no_stc_reference():
    """
    INV-AS6 : aucun fichier engine/* ne référence STC,
    save_the_children, cba_export, ou renderer.
    RÈGLE-M12-02 enforced par AST.
    """
    if not ENGINE_DIR.exists():
        pytest.skip("engine/ absent — milestone non démarré")

    forbidden_patterns = [
        "stc",
        "save_the_children",
        "save the children",
        "cba_export",
        "renderer",
        "cba_renderer",
    ]
    violations: list[str] = []

    for py_file in ENGINE_DIR.rglob("*.py"):
        text = _collect_text(py_file)
        for pattern in forbidden_patterns:
            if pattern in text:
                violations.append(f"{py_file.relative_to('.')} contient '{pattern}'")

    assert not violations, (
        f"INV-AS6 / RÈGLE-M12-02 violé — {len(violations)} référence(s) STC "
        f"dans engine/ :\n" + "\n".join(f"  🛑 {v}" for v in violations)
    )


def test_engine_does_not_import_export_or_renderer_namespaces():
    """
    INV-AS12/AS13 : aucun fichier engine/* n'importe
    des namespaces export, renderer, ou cba_exporter.
    """
    if not ENGINE_DIR.exists():
        pytest.skip("engine/ absent — milestone non démarré")

    forbidden_namespaces = [
        "exports",
        "render",
        "cba_exporter",
        "stc_cba",
        "adapters",
        "cba_export",
    ]
    violations: list[str] = []

    for py_file in ENGINE_DIR.rglob("*.py"):
        for imp in _collect_imports(py_file):
            for ns in forbidden_namespaces:
                if imp == ns or imp.startswith(ns + "."):
                    violations.append(f"{py_file.relative_to('.')} importe '{imp}'")

    assert not violations, (
        f"INV-AS12/AS13 violé — {len(violations)} import(s) renderer/export "
        f"dans engine/ :\n" + "\n".join(f"  🛑 {v}" for v in violations)
    )
