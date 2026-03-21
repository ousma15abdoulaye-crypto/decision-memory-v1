"""Racine du service sur sys.path — imports `prompts.*` depuis la racine du monorepo."""

from __future__ import annotations

import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parents[1]
_root = str(_backend_root)
if _root not in sys.path:
    sys.path.insert(0, _root)
# Monorepo : classifieur ARCH-01 sous src/annotation (import depuis backend.py)
_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
