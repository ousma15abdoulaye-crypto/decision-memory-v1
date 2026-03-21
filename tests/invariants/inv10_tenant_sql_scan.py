"""Helpers partagés — scan statique SQL vs tables RLS (migration 051).

Utilisé par test_inv_10_tenant_isolation (un seul endroit, revue PERF).
Ne couvre pas les f-strings SQL dynamiques (limite AST).
"""

from __future__ import annotations

import ast
import re
import warnings
from pathlib import Path

# Tables avec RLS tenant dans alembic 051 (public.<table>).
TENANT_SCOPED_TABLES: frozenset[str] = frozenset(
    {"cases", "criteria", "supplier_scores", "pipeline_runs"}
)

# Lectures globales suivies (pas RLS 051) — avertissement, pas échec.
_WARNING_SCOPED_TABLES: frozenset[str] = frozenset({"vendors"})

# Requêtes connues sûres : sous-chaîne normalisée (espaces condensés, lower).
_SQL_ALLOWLIST_NORMALIZED: tuple[tuple[str, str], ...] = (
    # Liste admin : auth obligatoire ; RLS DB en prod si rôle applicatif non superuser.
    ("src/api/cases.py", "select * from cases order by created_at desc"),
)

def _normalize_sql_snippet(s: str) -> str:
    return " ".join(s.lower().split())


def _first_from_table(sl: str, tables: frozenset[str]) -> str | None:
    """Première table `FROM`/`JOIN` parmi `tables` (re.IGNORECASE sur le motif)."""
    for t in tables:
        if re.search(rf"\bfrom\s+(?:public\.)?{re.escape(t)}\b", sl, flags=re.IGNORECASE):
            return t
        if re.search(rf"\bjoin\s+(?:public\.)?{re.escape(t)}\b", sl, flags=re.IGNORECASE):
            return t
    return None


def _sql_fragment_has_tenant_scope(sl: str) -> bool:
    """Heuristique : filtre tenant / dossier / propriétaire / clé métier."""
    s = sl.lower()
    if "tenant_id" in s:
        return True
    if "case_id" in s:
        return True
    if re.search(r"\borg_id\s*=", s):
        return True
    if re.search(r"\bowner_id\s*=", s):
        return True
    if re.search(r"\buser_id\s*=", s):
        return True
    if re.search(r"\bwhere\b.+\bid\s*=", s, flags=re.DOTALL):
        return True
    # Fournisseurs : requêtes ciblées par identité (hors liste globale is_active).
    if "fingerprint" in s:
        return True
    if re.search(r"\bvendor_id\s*[=~]", s):
        return True
    return False


def _is_allowlisted(relative_path: str, sl: str) -> bool:
    norm = _normalize_sql_snippet(sl)
    rel = relative_path.replace("\\", "/")
    for prefix, needle in _SQL_ALLOWLIST_NORMALIZED:
        if rel.endswith(prefix) or rel == prefix or f"/{prefix}" in f"/{rel}":
            if needle in norm:
                return True
    return False


def _joinedstr_sql_approx(node: ast.JoinedStr) -> str:
    """Recompose une approximation SQL pour f\"\"\"…{x}…\"\"\" (parties statiques)."""
    parts: list[str] = []
    for v in node.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            parts.append(v.value)
        # FormattedValue : ignorer la valeur, garder un marqueur court
        elif isinstance(v, ast.FormattedValue):
            parts.append(" ? ")
    return "".join(parts)


def iter_sql_select_strings_from_py(source: str) -> list[tuple[str, int]]:
    """Extrait (littéral SQL approx, n° ligne) pour str et f-strings SELECT…FROM."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value
            low = v.lower()
            if "select" in low and "from" in low:
                out.append((v, node.lineno or 1))
        elif isinstance(node, ast.JoinedStr):
            approx = _joinedstr_sql_approx(node)
            low = approx.lower()
            if "select" in low and "from" in low:
                out.append((approx, node.lineno or 1))
    return out


def scan_src_violations(repo_root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """
    Parcourt src/**/*.py : SELECT touchant une table RLS sans indice de périmètre.

    Retourne (violations_nouvelles, avertissements_écarts_connus).
    """
    src_root = repo_root / "src"
    violations: list[dict[str, str]] = []
    gap_hits: list[dict[str, str]] = []

    for path in sorted(src_root.rglob("*.py")):
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for chunk, chunk_line in iter_sql_select_strings_from_py(text):
            sl = chunk.lower()
            t_rls = _first_from_table(sl, TENANT_SCOPED_TABLES)
            t_warn = _first_from_table(sl, _WARNING_SCOPED_TABLES)
            if t_rls is None and t_warn is None:
                continue
            if _sql_fragment_has_tenant_scope(sl):
                continue
            if _is_allowlisted(rel, chunk):
                continue

            preview = " ".join(chunk.split())[:120]
            line_no = chunk_line
            needle = chunk.strip()[:40] if len(chunk.strip()) > 20 else None
            if needle:
                for i, line in enumerate(lines, start=1):
                    if needle in line:
                        line_no = i
                        break

            if t_rls:
                violations.append(
                    {
                        "file": rel,
                        "line": str(line_no),
                        "table": t_rls,
                        "sql_preview": preview,
                    }
                )
            elif t_warn:
                gap_hits.append(
                    {
                        "file": rel,
                        "line": str(line_no),
                        "table": t_warn,
                        "sql_preview": preview,
                    }
                )

    return violations, gap_hits


def warn_known_gaps(gap_hits: list[dict[str, str]]) -> None:
    for w in gap_hits:
        warnings.warn(
            f"Known gap R7 (hors tables RLS 051): {w['file']}:{w['line']} "
            f"table={w['table']} — {w['sql_preview']}",
            stacklevel=1,
        )
