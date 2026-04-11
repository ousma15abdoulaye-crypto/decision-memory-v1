#!/usr/bin/env python3
"""Gate V53 — aucun import de ``rag_service`` dans ``src/`` hors exceptions explicites.

Autorisé :

- ``src/memory/rag_service.py`` (module lui-même)
- ``src/agent/handlers.py`` — handler **document_corpus** / RAG M12 (mandat v52)

Exécution : ``python scripts/check_v53_no_rag_import_in_src.py``
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

_RAG_SERVICE_IMPORT_ALLOWED = frozenset(
    {
        Path("src/agent/handlers.py"),
    }
)


def main() -> int:
    pat = re.compile(
        r"^\s*(?:from\s+src\.memory\.rag_service|import\s+src\.memory\.rag_service)",
        re.MULTILINE,
    )
    violations: list[str] = []
    for path in SRC.rglob("*.py"):
        if path.name == "rag_service.py" and path.parent.name == "memory":
            continue
        rel = path.relative_to(ROOT)
        if rel.as_posix() in {p.as_posix() for p in _RAG_SERVICE_IMPORT_ALLOWED}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if pat.search(text):
            violations.append(str(rel))
    if violations:
        print("V53 gate: rag_service importé depuis src/ hors rag_service.py :")
        for v in sorted(violations):
            print(f"  - {v}")
        return 1
    print(
        "V53 gate: OK — aucun import rag_service hors memory/rag_service.py "
        "et allowlist handlers.py"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
