#!/usr/bin/env python3
"""Exporte le schéma OpenAPI de ``main:app`` (point d'entrée Railway).

Requiert ``DATABASE_URL`` (import de ``main`` charge ``src.db``).

Usage:
  python scripts/export_openapi_main_app.py --out frontend-v51/openapi-snapshot.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export OpenAPI depuis main:app")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("frontend-v51/openapi-snapshot.json"),
        help="Fichier JSON de sortie",
    )
    parser.add_argument(
        "--min-paths",
        type=int,
        default=8,
        help="Échoue si moins de chemins dans paths (sanity check)",
    )
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL"):
        print("export_openapi_main_app: DATABASE_URL manquant", file=sys.stderr)
        return 2

    # Racine dépôt sur sys.path (workflows sans PYTHONPATH explicite)
    _root = Path(__file__).resolve().parent.parent
    _rs = str(_root)
    if _rs not in sys.path:
        sys.path.insert(0, _rs)

    from main import app

    schema = app.openapi()
    paths = schema.get("paths") or {}
    if len(paths) < args.min_paths:
        print(
            f"export_openapi_main_app: seulement {len(paths)} paths (< {args.min_paths})",
            file=sys.stderr,
        )
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote {args.out} ({len(paths)} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
