#!/usr/bin/env python3
"""Gate V53 — aucun import de ``rag_service`` dans ``src/`` hors module mémoire.

Exécution : ``python scripts/check_v53_no_rag_import_in_src.py``
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def main() -> int:
    pat = re.compile(
        r"^\s*(?:from\s+src\.memory\.rag_service|import\s+src\.memory\.rag_service)",
        re.MULTILINE,
    )
    violations: list[str] = []
    for path in SRC.rglob("*.py"):
        if path.name == "rag_service.py" and path.parent.name == "memory":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if pat.search(text):
            violations.append(str(path.relative_to(ROOT)))
    if violations:
        print("V53 gate: rag_service importé depuis src/ hors rag_service.py :")
        for v in sorted(violations):
            print(f"  - {v}")
        return 1
    print("V53 gate: OK — aucun import rag_service dans src/ (hors rag_service.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
