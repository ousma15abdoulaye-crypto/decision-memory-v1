#!/usr/bin/env python3
"""Collecte métriques workspace — point d'entrée industrialisé.

Exemple ::
  set DATABASE_URL=postgresql://...
  set WORKSPACE_ID=<uuid>
  python scripts/collect_workspace_metrics.py -o out.json

Schéma JSON : ``config/schemas/dms_workspace_metrics_v1_1.schema.json``
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.metrics.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
