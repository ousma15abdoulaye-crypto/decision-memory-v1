"""Smoke — scripts/ingest_embeddings.py --dry-run (sans PostgreSQL)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def test_ingest_embeddings_dry_run_exits_zero() -> None:
    script = _ROOT / "scripts" / "ingest_embeddings.py"
    fixture = _ROOT / "tests" / "fixtures" / "m12_rag_ingest_sample.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input",
            str(fixture),
            "--tenant-id",
            "00000000-0000-0000-0000-000000000001",
            "--dry-run",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
