"""
DT-006 -- Boundary gate: Couche A must NOT import Couche B business sub-modules.

Rule (prefix-based):
  Forbidden: imports from couche_b sub-modules EXCEPT normalisation
             (mercuriale, procurement_dict, resolvers, etc.)
  Allowed:
    - `import src.couche_b` / `from src.couche_b import ...` (facade)
    - `from src.couche_b.normalisation...` (public normalization API --
      DT-006 exception: facade does not re-export normalize_batch in V3.3.2;
      documented in M-SCORING-ENGINE milestone)

Forbidden sub-modules (couche_b business logic Couche A must NOT touch):
  mercuriale, procurement_dict, resolvers (direct sub-module bypass)

Scope: all .py files under src/couche_a/price_check/
       + src/api/routers/price_check.py
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COUCHE_A_PRICE_CHECK = REPO_ROOT / "src" / "couche_a" / "price_check"
ROUTER_FILE = REPO_ROOT / "src" / "api" / "routers" / "price_check.py"

# Sub-modules of couche_b that Couche A must NEVER import from
FORBIDDEN_SUBMODULE_PREFIXES = (
    "src.couche_b.mercuriale",
    "couche_b.mercuriale",
    "src.couche_b.resolvers",
    "couche_b.resolvers",
    "src.couche_b.procurement_dict",
    "couche_b.procurement_dict",
)

ALLOWED_EXACT = (
    "src.couche_b",
    "couche_b",
)


def _collect_imports(source: str) -> list[tuple[str, int]]:
    """Return list of (module_str, lineno) for all import statements."""
    tree = ast.parse(source)
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append((module, node.lineno))
    return imports


def _check_file(path: Path) -> list[str]:
    """Return list of violation strings for a given file."""
    source = path.read_text(encoding="utf-8")
    violations = []
    for module, lineno in _collect_imports(source):
        for prefix in FORBIDDEN_SUBMODULE_PREFIXES:
            if module.startswith(prefix):
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}:{lineno} "
                    f"FORBIDDEN import '{module}' (business Couche B sub-module)"
                )
    return violations


def _couche_a_price_check_files() -> list[Path]:
    if not COUCHE_A_PRICE_CHECK.exists():
        return []
    return list(COUCHE_A_PRICE_CHECK.rglob("*.py"))


def _all_scope_files() -> list[Path]:
    files = _couche_a_price_check_files()
    if ROUTER_FILE.exists():
        files.append(ROUTER_FILE)
    return files


@pytest.mark.skipif(
    not COUCHE_A_PRICE_CHECK.exists(),
    reason="src/couche_a/price_check not yet created",
)
def test_dt006_no_business_couche_b_submodule_imports():
    """DT-006: No file in price_check scope imports couche_b business sub-modules."""
    scope_files = _all_scope_files()
    assert scope_files, "No files found in price_check scope -- check paths."

    all_violations: list[str] = []
    for f in scope_files:
        all_violations.extend(_check_file(f))

    assert not all_violations, (
        "DT-006 VIOLATION: business Couche B sub-module imports detected:\n"
        + "\n".join(all_violations)
    )


@pytest.mark.skipif(
    not COUCHE_A_PRICE_CHECK.exists(),
    reason="src/couche_a/price_check not yet created",
)
def test_dt006_scope_files_exist():
    """DT-006: At least schemas.py and engine.py must be present."""
    schemas = COUCHE_A_PRICE_CHECK / "schemas.py"
    engine = COUCHE_A_PRICE_CHECK / "engine.py"
    assert schemas.exists(), f"Missing {schemas.relative_to(REPO_ROOT)}"
    assert engine.exists(), f"Missing {engine.relative_to(REPO_ROOT)}"
