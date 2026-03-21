#!/usr/bin/env python3
"""List FastAPI routes: auth (get_current_user) and case/document guards in dep trees.

Usage:
  python scripts/audit_fastapi_auth_coverage.py
  python scripts/audit_fastapi_auth_coverage.py --app main:app
  python scripts/audit_fastapi_auth_coverage.py --fail-prefix /api/cases
  python scripts/audit_fastapi_auth_coverage.py --app src.api.main:app \\
      --fail-sensitive-prefix /api/cases --report-md docs/audits/artifacts/audit_report.md

Heuristic limits:
  - Only inspects FastAPI dependency trees (not guards called inside endpoint bodies).
  - Paths are "sensitive" if they contain a path param named like case_id / document_id / job_id.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_CASE_GUARD_NAMES = frozenset(
    {
        "require_case_access",
        "require_case_access_dep",
        "require_document_case_access",
        "require_document_case_access_dep",
        "require_case_tenant_org",
    }
)


def _dep_has_current_user(dep: Any, depth: int = 0) -> bool:
    if dep is None or depth > 40:
        return False
    call = getattr(dep, "call", None)
    if call is not None:
        name = getattr(call, "__name__", "")
        mod = getattr(call, "__module__", "")
        if name == "get_current_user" and mod.endswith("dependencies"):
            return True
    for sub in getattr(dep, "dependencies", None) or ():
        if _dep_has_current_user(sub, depth + 1):
            return True
    return False


def _dep_has_case_guard(dep: Any, depth: int = 0) -> bool:
    if dep is None or depth > 40:
        return False
    call = getattr(dep, "call", None)
    if call is not None:
        name = getattr(call, "__name__", "")
        if name in _CASE_GUARD_NAMES:
            return True
    for sub in getattr(dep, "dependencies", None) or ():
        if _dep_has_case_guard(sub, depth + 1):
            return True
    return False


def _path_has_sensitive_param(path: str) -> bool:
    p = path.lower()
    for token in ("{case_id}", "{document_id}", "{job_id}"):
        if token in p:
            return True
    return False


def _route_rows(app) -> list[tuple[str, str, bool, bool, bool]]:
    rows: list[tuple[str, str, bool, bool, bool]] = []
    for r in app.routes:
        methods = getattr(r, "methods", None) or frozenset()
        path = getattr(r, "path", "") or ""
        dep = getattr(r, "dependant", None)
        if not methods or not path:
            continue
        has_user = _dep_has_current_user(dep)
        has_guard = _dep_has_case_guard(dep)
        sensitive = _path_has_sensitive_param(path)
        for m in sorted(methods):
            if m == "HEAD":
                continue
            rows.append((m, path, has_user, has_guard, sensitive))
    rows.sort(key=lambda x: (x[1], x[0]))
    return rows


def _write_report_md(
    path: Path, app_label: str, rows: list[tuple[str, str, bool, bool, bool]]
) -> None:
    lines = [
        f"# FastAPI auth / case-guard audit — `{app_label}`",
        "",
        "| method | bearer (get_current_user) | case_guard | sensitive_path | path |",
        "| --- | --- | --- | --- | --- |",
    ]
    for method, pth, ok, cg, sens in rows:
        lines.append(
            f"| {method} | {'yes' if ok else 'NO'} | {'yes' if cg else 'no'} | "
            f"{'yes' if sens else 'no'} | `{pth}` |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_report_csv(
    path: Path, rows: list[tuple[str, str, bool, bool, bool]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["method", "path", "has_bearer", "has_case_guard", "sensitive_path_param"]
        )
        for method, pth, ok, cg, sens in rows:
            w.writerow([method, pth, ok, cg, sens])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--app",
        default="main:app",
        help="module:attribute for FastAPI app (default: main:app)",
    )
    p.add_argument(
        "--fail-prefix",
        action="append",
        default=[],
        help="Exit 1 if a route under this prefix has no get_current_user in dep tree",
    )
    p.add_argument(
        "--fail-sensitive-prefix",
        action="append",
        default=[],
        help=(
            "Exit 1 if a route path starts with this prefix, declares "
            "{case_id}/{document_id}/{job_id}, and has no case-guard in dep tree"
        ),
    )
    p.add_argument(
        "--report-md",
        default="",
        help="Write Markdown table to this path",
    )
    p.add_argument(
        "--report-csv",
        default="",
        help="Write CSV to this path",
    )
    args = p.parse_args()

    mod_name, attr = args.app.split(":", 1)
    mod = importlib.import_module(mod_name)
    app = getattr(mod, attr)

    rows = _route_rows(app)
    print(f"{'METHOD':<8} {'AUTH':<5} {'GUARD':<6} {'SENS':<5} PATH")
    print("-" * 80)
    for method, path, ok, cg, sens in rows:
        print(
            f"{method:<8} {'yes' if ok else 'NO':<5} "
            f"{'yes' if cg else 'no':<6} {'yes' if sens else 'no':<5} {path}"
        )

    if args.report_md:
        _write_report_md(Path(args.report_md), args.app, rows)
    if args.report_csv:
        _write_report_csv(Path(args.report_csv), rows)

    violations_auth: list[tuple[str, str]] = []
    for prefix in args.fail_prefix:
        for method, path, ok, _cg, _sens in rows:
            if path.startswith(prefix) and not ok:
                violations_auth.append((method, path))

    violations_guard: list[tuple[str, str]] = []
    for prefix in args.fail_sensitive_prefix:
        for method, path, _ok, cg, sens in rows:
            if path.startswith(prefix) and sens and not cg:
                violations_guard.append((method, path))

    if violations_auth:
        print(
            "\nFAIL — routes missing get_current_user under --fail-prefix:",
            file=sys.stderr,
        )
        for m, path in violations_auth:
            print(f"  {m} {path}", file=sys.stderr)
        return 1
    if violations_guard:
        print(
            "\nFAIL — sensitive routes missing case-guard under --fail-sensitive-prefix:",
            file=sys.stderr,
        )
        for m, path in violations_guard:
            print(f"  {m} {path}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
