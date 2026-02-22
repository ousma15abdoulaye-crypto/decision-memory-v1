"""
ADR-0009 — Constitution compliance gate.

Enforces:
  1. No decisional fields in PriceCheckResult or OffreInput schemas.
  2. Router prefix is /price-check (not /scoring).
  3. No writes to submission_scores or supplier_scores from price_check scope.

Scope:
  src/couche_a/price_check/schemas.py
  src/couche_a/price_check/engine.py
  src/api/routers/price_check.py
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COUCHE_A_PRICE_CHECK = REPO_ROOT / "src" / "couche_a" / "price_check"
ROUTER_FILE = REPO_ROOT / "src" / "api" / "routers" / "price_check.py"

DECISIONAL_FIELDS = {
    "rank",
    "winner",
    "recommendation",
    "selected",
    "best_offer",
    "shortlist",
    "classement",
    "gagnant",
    "ranking",
}

FORBIDDEN_WRITE_TARGETS = (
    "submission_scores",
    "supplier_scores",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _all_scope_files() -> list[Path]:
    files = (
        list(COUCHE_A_PRICE_CHECK.rglob("*.py"))
        if COUCHE_A_PRICE_CHECK.exists()
        else []
    )
    if ROUTER_FILE.exists():
        files.append(ROUTER_FILE)
    return files


@pytest.mark.skipif(
    not COUCHE_A_PRICE_CHECK.exists(),
    reason="src/couche_a/price_check not yet created",
)
def test_constitution_no_decisional_fields_in_schemas():
    """ADR-0009: PriceCheckResult must contain zero decisional fields."""
    schemas_file = COUCHE_A_PRICE_CHECK / "schemas.py"
    if not schemas_file.exists():
        pytest.skip("schemas.py not yet created")

    source = _read(schemas_file)
    tree = ast.parse(source)
    violations = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            for child in ast.walk(node):
                if isinstance(child, ast.AnnAssign):
                    field_name = (
                        child.target.id if isinstance(child.target, ast.Name) else None
                    )
                    if field_name and field_name.lower() in DECISIONAL_FIELDS:
                        violations.append(
                            f"schemas.py:{child.col_offset} "
                            f"FORBIDDEN decisional field '{field_name}'"
                        )

    assert (
        not violations
    ), "Constitution violation: decisional fields detected in schemas:\n" + "\n".join(
        violations
    )


@pytest.mark.skipif(
    not ROUTER_FILE.exists(),
    reason="price_check router not yet created",
)
def test_constitution_router_prefix_is_price_check():
    """ADR-0009: Router must use /price-check prefix, not /scoring."""
    import ast as _ast

    source = _read(ROUTER_FILE)
    assert (
        "/price-check" in source
    ), "Router must declare prefix='/price-check' (ADR-0009)"
    # AST-level check: no APIRouter instantiated with prefix starting with /scoring
    tree = _ast.parse(source)
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Call):
            for kw in node.keywords:
                if kw.arg == "prefix" and isinstance(kw.value, _ast.Constant):
                    val: str = str(kw.value.value)
                    assert not val.startswith("/scoring"), (
                        f"APIRouter prefix '{val}' MUST NOT start with /scoring "
                        "(Constitution DMS V3.3.2)"
                    )


@pytest.mark.skipif(
    not COUCHE_A_PRICE_CHECK.exists(),
    reason="src/couche_a/price_check not yet created",
)
def test_constitution_no_write_to_score_tables():
    """ADR-0009: price_check scope must never write to submission/supplier_scores."""
    scope_files = _all_scope_files()
    violations = []
    for f in scope_files:
        source = _read(f)
        for target in FORBIDDEN_WRITE_TARGETS:
            # Look for INSERT INTO or UPDATE ... <table> patterns
            pattern = re.compile(
                r"(INSERT\s+INTO|UPDATE)\s+" + re.escape(target),
                re.IGNORECASE,
            )
            for m in pattern.finditer(source):
                lineno = source[: m.start()].count("\n") + 1
                violations.append(
                    f"{f.relative_to(REPO_ROOT)}:{lineno} "
                    f"FORBIDDEN write to '{target}'"
                )

    assert (
        not violations
    ), "Constitution violation: write to score tables detected:\n" + "\n".join(
        violations
    )
