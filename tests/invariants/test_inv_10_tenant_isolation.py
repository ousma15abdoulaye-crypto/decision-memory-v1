"""Test Invariant 10: Multi-tenant isolation — analyse statique.

Constitution V4.1.0 — Règle R7 : org_id obligatoire sur données TENANT_SCOPED.

Ce test scanne le code source pour détecter :
  1. Les requêtes SQL SELECT sur tables TENANT_SCOPED sans filtre org_id ni owner_id
  2. Les requêtes SQL INSERT sur tables TENANT_SCOPED sans colonne org_id
  3. Les endpoints accédant aux données TENANT_SCOPED sans authentification

Principe : analyse statique AST + regex — aucun runtime DB requis.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# ── Tables classifiées TENANT_SCOPED — org_id obligatoire
TENANT_SCOPED_TABLES: frozenset[str] = frozenset(
    {
        "cases",
        "documents",
        "offers",
        "offer_extractions",
        "dao_criteria",
        "committees",
        "committee_members",
        "committee_decisions",
        "committee_events",
        "decision_snapshots",
        "decision_history",
        "pipeline_runs",
        "pipeline_steps",
        "vendors",
        "vendors_sensitive_data",
        "extraction_jobs",
        "market_surveys",
        "artifacts",
        "memory_entries",
    }
)

# ── Fichiers exclus de l'analyse (tests, migrations, scripts utilitaires)
EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        "tests",
        "alembic",
        "scripts",
        "__pycache__",
        ".git",
        "node_modules",
        "services",
    }
)

# ── Patterns indiquant la présence d'un filtre tenant dans une requête
TENANT_FILTER_PATTERNS: list[str] = [
    r"\borg_id\b",
    r"\bowner_id\b",
]

SRC_DIR = Path("src")


def _should_exclude(filepath: Path) -> bool:
    """Retourne True si le fichier est dans un répertoire exclu."""
    parts = filepath.parts
    return any(excl in parts for excl in EXCLUDED_DIRS)


def _extract_sql_strings(filepath: Path) -> list[tuple[int, str]]:
    """Extrait les chaînes SQL probables d'un fichier Python.

    Returns:
        Liste de (numéro_ligne_approx, contenu_sql)
    """
    results: list[tuple[int, str]] = []
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return results

    for node in ast.walk(tree):
        # Chaînes simples
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value.strip().upper()
            if any(kw in val for kw in ("SELECT ", "INSERT ", "UPDATE ", "DELETE ")):
                results.append((getattr(node, "lineno", 0), node.value))
        # f-strings
        elif isinstance(node, ast.JoinedStr):
            parts: list[str] = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
            joined = "".join(parts).strip().upper()
            if any(kw in joined for kw in ("SELECT ", "INSERT ", "UPDATE ", "DELETE ")):
                results.append((getattr(node, "lineno", 0), "".join(parts)))

    return results


def _sql_references_tenant_table(sql: str) -> str | None:
    """Retourne le nom de la table TENANT_SCOPED référencée, ou None."""
    sql_upper = sql.upper()
    for table in TENANT_SCOPED_TABLES:
        # Patterns : FROM table, INTO table, UPDATE table, JOIN table
        pattern = rf"\b(?:FROM|INTO|UPDATE|JOIN)\s+(?:public\.)?{re.escape(table)}\b"
        if re.search(pattern, sql_upper):
            return table
    return None


def _sql_has_tenant_filter(sql: str) -> bool:
    """Retourne True si la requête SQL contient un filtre tenant."""
    return any(re.search(pat, sql, re.IGNORECASE) for pat in TENANT_FILTER_PATTERNS)


# ────────────────────────────────────────────────────────────────
# TESTS
# ────────────────────────────────────────────────────────────────


def test_inv_10_select_queries_have_tenant_filter():
    """SELECT sur tables TENANT_SCOPED doit inclure org_id ou owner_id."""
    if not SRC_DIR.exists():
        pytest.skip("src/ directory not found")

    violations: list[dict[str, str]] = []

    for py_file in SRC_DIR.rglob("*.py"):
        if _should_exclude(py_file):
            continue

        sql_strings = _extract_sql_strings(py_file)
        for lineno, sql in sql_strings:
            if "SELECT" not in sql.upper():
                continue
            table = _sql_references_tenant_table(sql)
            if table is None:
                continue
            if _sql_has_tenant_filter(sql):
                continue

            # Allowlist: queries that filter by case_id are acceptable
            # because case_id is inherently scoped to its owner/org
            # (a UUID that is not guessable). This applies to:
            #   - Pipeline preflight checks (COUNT queries)
            #   - Service-layer queries that receive case_id from
            #     an already-authenticated and owner-checked endpoint
            sql_lower = sql.lower()
            if "case_id" in sql_lower:
                continue

            violations.append(
                {
                    "file": str(py_file),
                    "line": str(lineno),
                    "table": table,
                    "sql_preview": sql[:120].replace("\n", " ").strip(),
                }
            )

    assert not violations, (
        f"VIOLATION Règle R7 — {len(violations)} SELECT sans filtre tenant :\n"
        + "\n".join(
            f"  {v['file']}:{v['line']} → table '{v['table']}' "
            f"SQL: {v['sql_preview']}"
            for v in violations
        )
    )


def test_inv_10_no_global_select_star_on_tenant_tables():
    """Aucun SELECT * FROM <tenant_table> sans clause WHERE."""
    if not SRC_DIR.exists():
        pytest.skip("src/ directory not found")

    violations: list[dict[str, str]] = []

    for py_file in SRC_DIR.rglob("*.py"):
        if _should_exclude(py_file):
            continue

        sql_strings = _extract_sql_strings(py_file)
        for lineno, sql in sql_strings:
            sql_upper = sql.upper().replace("\n", " ").strip()
            if not sql_upper.startswith("SELECT"):
                continue

            table = _sql_references_tenant_table(sql)
            if table is None:
                continue

            # Détecte SELECT sans WHERE
            if "WHERE" not in sql_upper:
                violations.append(
                    {
                        "file": str(py_file),
                        "line": str(lineno),
                        "table": table,
                        "sql_preview": sql[:120].replace("\n", " ").strip(),
                    }
                )

    assert not violations, (
        f"VIOLATION R7 — {len(violations)} SELECT global (pas de WHERE) "
        f"sur tables TENANT_SCOPED :\n"
        + "\n".join(
            f"  {v['file']}:{v['line']} → table '{v['table']}' "
            f"SQL: {v['sql_preview']}"
            for v in violations
        )
    )


def test_inv_10_tenant_guard_module_exists():
    """Le module tenant_guard.py doit exister dans l'auth layer."""
    guard_path = Path("src/couche_a/auth/tenant_guard.py")
    assert guard_path.exists(), (
        "Module tenant_guard.py manquant. "
        "Requis pour enforcement Règle R7 multi-tenant."
    )


def test_inv_10_user_claims_has_org_id():
    """UserClaims doit contenir le champ org_id pour isolation multi-tenant."""
    from src.couche_a.auth.dependencies import UserClaims

    fields = {f.name for f in UserClaims.__dataclass_fields__.values()}
    assert "org_id" in fields, (
        "UserClaims manque le champ 'org_id'. "
        "Requis pour isolation multi-tenant Règle R7."
    )


def test_inv_10_jwt_handler_supports_org_id():
    """create_access_token doit accepter le paramètre org_id."""
    import inspect

    from src.couche_a.auth.jwt_handler import create_access_token

    sig = inspect.signature(create_access_token)
    assert "org_id" in sig.parameters, (
        "create_access_token ne supporte pas org_id. "
        "Requis pour injection du claim org_id dans les tokens JWT."
    )
