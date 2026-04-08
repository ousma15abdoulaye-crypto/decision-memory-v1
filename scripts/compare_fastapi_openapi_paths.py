#!/usr/bin/env python3
"""Compare les ensembles de chemins OpenAPI ``main:app`` vs ``src.api.main:app``.

Utile pour la dérive P0-OPS-01 (ADR-DUAL-FASTAPI-ENTRYPOINTS). Requiert DATABASE_URL.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    if not os.environ.get("DATABASE_URL"):
        print("compare_fastapi_openapi_paths: DATABASE_URL manquant", file=sys.stderr)
        return 2
    from main import app as main_app
    from src.api.main import app as modular_app

    p_main = set((main_app.openapi().get("paths") or {}).keys())
    p_mod = set((modular_app.openapi().get("paths") or {}).keys())
    only_main = sorted(p_main - p_mod)
    only_mod = sorted(p_mod - p_main)
    print(f"main:app paths: {len(p_main)}")
    print(f"src.api.main:app paths: {len(p_mod)}")
    if only_main:
        print(f"Only on main:app ({len(only_main)}): {only_main[:25]}...")
    if only_mod:
        print(f"Only on modular ({len(only_mod)}): {only_mod[:25]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
