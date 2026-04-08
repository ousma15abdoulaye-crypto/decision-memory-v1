#!/usr/bin/env python3
"""Échoue si ``types/api.ts`` ressemble au stub openapi-typescript vide (paths vides)."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "frontend-v51/types/api.ts")
    text = path.read_text(encoding="utf-8")
    if (
        re.search(r"export\s+(interface|type)\s+paths\s*[=:{]", text)
        and text.count('"/') < 4
    ):
        print(
            f"{path}: peu ou pas de chemins HTTP typés — régénérer (export OpenAPI + openapi-typescript)",
            file=sys.stderr,
        )
        return 1
    if len(text) < 400:
        print(f"{path}: fichier trop court ({len(text)} o)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
