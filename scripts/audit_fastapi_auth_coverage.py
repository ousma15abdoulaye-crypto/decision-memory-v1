#!/usr/bin/env python3
"""List FastAPI routes and whether the dependency tree includes get_current_user.

Usage:
  python scripts/audit_fastapi_auth_coverage.py
  python scripts/audit_fastapi_auth_coverage.py --app main:app
  python scripts/audit_fastapi_auth_coverage.py --fail-prefix /api/cases

Exit code 1 if any route path starts with --fail-prefix and lacks get_current_user
in its dependency tree (heuristic for CI gates).
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


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


def _route_rows(app) -> list[tuple[str, str, bool]]:
    rows: list[tuple[str, str, bool]] = []
    for r in app.routes:
        methods = getattr(r, "methods", None) or frozenset()
        path = getattr(r, "path", "") or ""
        dep = getattr(r, "dependant", None)
        if not methods or not path:
            continue
        ok = _dep_has_current_user(dep)
        for m in sorted(methods):
            if m == "HEAD":
                continue
            rows.append((m, path, ok))
    rows.sort(key=lambda x: (x[1], x[0]))
    return rows


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
        help="If set, exit 1 when a route under this prefix has no get_current_user",
    )
    args = p.parse_args()

    mod_name, attr = args.app.split(":", 1)
    mod = importlib.import_module(mod_name)
    app = getattr(mod, attr)

    rows = _route_rows(app)
    print(f"{'METHOD':<8} {'AUTH':<5} PATH")
    print("-" * 72)
    for method, path, ok in rows:
        print(f"{method:<8} {'yes' if ok else 'NO':<5} {path}")

    violations: list[tuple[str, str]] = []
    for prefix in args.fail_prefix:
        for method, path, ok in rows:
            if path.startswith(prefix) and not ok:
                violations.append((method, path))

    if violations:
        print("\nFAIL — routes missing get_current_user under fail-prefix:", file=sys.stderr)
        for m, path in violations:
            print(f"  {m} {path}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
