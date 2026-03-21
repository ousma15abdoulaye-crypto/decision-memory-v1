"""Invariant tests — multi-tenant isolation (static analysis).

These tests verify, at the code level, that multi-tenant isolation
patterns are respected across the codebase.

Gate : 🔴 BLOQUANT CI (actif dès M-TESTS.done)
REF  : Constitution V3.3.2 §2 — isolation multi-tenant
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

# ──────────────────────────────────────────────────────────────
# Tables that MUST be scoped by org_id in every query
# ──────────────────────────────────────────────────────────────

TENANT_SCOPED_TABLES = {
    "criteria",
    "committees",
    "market_surveys",
    "price_anomaly_alerts",
    "survey_campaigns",
    "survey_campaign_items",
    "survey_campaign_zones",
    "decision_history",
}

# Directories containing application SQL queries
SRC_DIRS = ["src"]

# Files that are ALLOWED to query without org_id (infra / setup / test)
ALLOWED_UNSCOPED_FILES = {
    "alembic",
    "tests",
    "scripts",
    "__pycache__",
    "conftest.py",
}

# Known pre-existing violations — documented in audit, require dedicated
# mandates to fix.  Keyed by (normalised file path, table).
# Each entry was catalogued in docs/audits/MULTI_TENANT_HARDENING_AUDIT.md.
_KNOWN_VIOLATIONS: set[tuple[str, str]] = {
    ("src/couche_a/committee/service.py", "committees"),
    ("src/couche_a/market/signal_engine.py", "market_surveys"),
}


def _is_allowed_path(filepath: str) -> bool:
    """Return True if the file is in an allowed (non-app) path."""
    parts = Path(filepath).parts
    return any(allowed in parts for allowed in ALLOWED_UNSCOPED_FILES)


def _find_sql_in_python(filepath: str) -> list[tuple[int, str]]:
    """Extract SQL string literals from a Python file.

    Returns list of (line_number, sql_fragment) tuples.
    """
    results = []
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return results

    for node in ast.walk(tree):
        # String constants
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value.strip()
            # Only interested in SQL-like strings
            if re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", val, re.IGNORECASE):
                results.append((getattr(node, "lineno", 0), val))
        # f-strings (JoinedStr) — extract string parts
        elif isinstance(node, ast.JoinedStr):
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
            joined = "".join(parts)
            if re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", joined, re.IGNORECASE):
                results.append((getattr(node, "lineno", 0), joined))

    return results


def _mentions_table(sql: str, table: str) -> bool:
    """Check if a SQL fragment references a given table."""
    # Match table name with word boundaries, possibly with schema prefix
    pattern = rf"\b(?:public\.)?{re.escape(table)}\b"
    return bool(re.search(pattern, sql, re.IGNORECASE))


def _has_org_id_filter(sql: str) -> bool:
    """Check if a SQL fragment includes an org_id filter."""
    # Look for org_id in WHERE clause or VALUES / INSERT columns
    return bool(re.search(r"\borg_id\b", sql, re.IGNORECASE))


def test_tenant_scoped_tables_have_org_id_in_queries():
    """Every SQL query touching a tenant-scoped table must include org_id.

    This is a static analysis check. It scans all Python files under src/
    for SQL strings that reference tenant-scoped tables and verifies they
    include an org_id filter or column.

    Pre-existing violations documented in the audit are tracked but do not
    block CI.  Only NEW violations cause a hard failure.

    False positives are possible for:
      - Schema DDL statements (CREATE TABLE, ALTER TABLE)
      - Comments mentioning table names
    These are filtered out.
    """
    violations = []
    known_hits = []

    for src_dir in SRC_DIRS:
        if not os.path.isdir(src_dir):
            continue

        for root, _dirs, files in os.walk(src_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                filepath = os.path.join(root, fname)

                if _is_allowed_path(filepath):
                    continue

                sql_fragments = _find_sql_in_python(filepath)

                for lineno, sql in sql_fragments:
                    # Skip DDL statements
                    if re.search(
                        r"\b(CREATE|ALTER|DROP)\s+(TABLE|INDEX|TRIGGER|POLICY|VIEW)\b",
                        sql,
                        re.IGNORECASE,
                    ):
                        continue

                    for table in TENANT_SCOPED_TABLES:
                        if _mentions_table(sql, table) and not _has_org_id_filter(sql):
                            norm = os.path.normpath(filepath)
                            entry = {
                                "file": filepath,
                                "line": lineno,
                                "table": table,
                                "sql_preview": sql[:120],
                            }
                            if (norm, table) in _KNOWN_VIOLATIONS:
                                known_hits.append(entry)
                            else:
                                violations.append(entry)

    # Log known violations for visibility
    if known_hits:
        import warnings

        warnings.warn(
            f"{len(known_hits)} known tenant isolation gap(s) — "
            f"see docs/audits/MULTI_TENANT_HARDENING_AUDIT.md",
            stacklevel=1,
        )

    if violations:
        msg = (
            f"NEW TENANT ISOLATION VIOLATION — {len(violations)} SQL query(ies) "
            f"touch tenant-scoped tables without org_id filter:\n"
        )
        for v in violations:
            msg += (
                f"  {v['file']}:{v['line']} — table '{v['table']}'\n"
                f"    SQL: {v['sql_preview']}...\n"
            )
        pytest.fail(msg)


def test_no_global_select_on_tenant_tables():
    """No SELECT * FROM <tenant_table> without WHERE org_id clause.

    Catches the most dangerous pattern: unbounded reads on
    tenant-scoped tables that would leak data across organisations.

    Pre-existing violations documented in the audit are tracked but do not
    block CI.  Only NEW violations cause a hard failure.
    """
    violations = []
    known_hits = []

    for src_dir in SRC_DIRS:
        if not os.path.isdir(src_dir):
            continue

        for root, _dirs, files in os.walk(src_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                filepath = os.path.join(root, fname)

                if _is_allowed_path(filepath):
                    continue

                try:
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                except (OSError, UnicodeDecodeError):
                    continue

                for table in TENANT_SCOPED_TABLES:
                    # Pattern: SELECT ... FROM table ... without WHERE org_id
                    pattern = rf"SELECT\s+.{{0,200}}\bFROM\s+(?:public\.)?{re.escape(table)}\b"
                    for match in re.finditer(
                        pattern, content, re.IGNORECASE | re.DOTALL
                    ):
                        # Check the surrounding context for org_id
                        start = max(0, match.start() - 50)
                        end = min(len(content), match.end() + 300)
                        context = content[start:end]

                        if not re.search(r"\borg_id\b", context, re.IGNORECASE):
                            # Find line number
                            line_num = content[: match.start()].count("\n") + 1
                            norm = os.path.normpath(filepath)
                            entry = {
                                "file": filepath,
                                "line": line_num,
                                "table": table,
                                "match": match.group()[:100],
                            }
                            if (norm, table) in _KNOWN_VIOLATIONS:
                                known_hits.append(entry)
                            else:
                                violations.append(entry)

    # Log known violations for visibility
    if known_hits:
        import warnings

        warnings.warn(
            f"{len(known_hits)} known global-read gap(s) — "
            f"see docs/audits/MULTI_TENANT_HARDENING_AUDIT.md",
            stacklevel=1,
        )

    if violations:
        msg = (
            f"NEW GLOBAL READ VIOLATION — {len(violations)} unbounded SELECT(s) "
            f"on tenant-scoped tables:\n"
        )
        for v in violations:
            msg += (
                f"  {v['file']}:{v['line']} — table '{v['table']}'\n"
                f"    Match: {v['match']}...\n"
            )
        pytest.fail(msg)


def test_rls_migration_exists():
    """Migration 051 must define RLS policies for tenant-scoped tables.

    Verifies that the RLS migration file exists and contains the
    expected policy creation statements.
    """
    migration_path = "alembic/versions/051_rls_tenant_isolation.py"
    assert os.path.isfile(migration_path), (
        f"RLS migration missing: {migration_path}. "
        "Multi-tenant DB enforcement requires RLS policies."
    )

    with open(migration_path, encoding="utf-8") as f:
        content = f.read()

    assert (
        "ENABLE ROW LEVEL SECURITY" in content
    ), "RLS migration must contain ENABLE ROW LEVEL SECURITY"
    assert (
        "CREATE POLICY" in content
    ), "RLS migration must contain CREATE POLICY statements"
    assert (
        "app.org_id" in content
    ), "RLS policies must reference app.org_id session variable"


def test_tenant_middleware_exists():
    """TenantContextMiddleware must exist and be importable."""
    middleware_path = "src/middleware/tenant_context.py"
    assert os.path.isfile(
        middleware_path
    ), f"Tenant middleware missing: {middleware_path}"

    with open(middleware_path, encoding="utf-8") as f:
        content = f.read()

    assert "TenantContextMiddleware" in content
    assert "app.org_id" in content
    assert "set_tenant_context" in content
