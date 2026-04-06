#!/usr/bin/env python3
"""Alias CLI — même comportement que ``inventory_m12_corpus_jsonl.py``.

Nom historique référencé dans ``docs/freeze/CONTEXT_ANCHOR.md``. Délègue au script canonique.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_CANON = Path(__file__).resolve().parent / "inventory_m12_corpus_jsonl.py"


def main() -> None:
    sys.argv[0] = str(_CANON)
    runpy.run_path(str(_CANON), run_name="__main__")


if __name__ == "__main__":
    main()
