"""CLI consolidation M12 (local JSONL, sans R2)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.annotation.m12_export_io import iter_m12_jsonl_lines


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_consolidate_two_inputs_last_file_wins(repo_root: Path, tmp_path: Path) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    out = tmp_path / "out.jsonl"
    line1 = {"content_hash": "same", "x": 1, "export_schema_version": "m12-v2"}
    line2 = {"content_hash": "same", "x": 2, "export_schema_version": "m12-v2"}
    a.write_text(json.dumps(line1) + "\n", encoding="utf-8")
    b.write_text(json.dumps(line2) + "\n", encoding="utf-8")
    r = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "consolidate_m12_corpus.py"),
            "-i",
            str(a),
            "-i",
            str(b),
            "-o",
            str(out),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    lines = list(iter_m12_jsonl_lines(out))
    assert len(lines) == 1
    assert lines[0]["x"] == 2


def test_consolidate_only_export_ok_filters(repo_root: Path, tmp_path: Path) -> None:
    p = tmp_path / "mix.jsonl"
    out = tmp_path / "out.jsonl"
    p.write_text(
        json.dumps(
            {
                "export_schema_version": "m12-v2",
                "export_ok": False,
                "content_hash": "a",
            }
        )
        + "\n"
        + json.dumps(
            {
                "export_schema_version": "m12-v2",
                "export_ok": True,
                "content_hash": "b",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "consolidate_m12_corpus.py"),
            "-i",
            str(p),
            "-o",
            str(out),
            "--only-export-ok",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    lines = list(iter_m12_jsonl_lines(out))
    assert len(lines) == 1
    assert lines[0]["content_hash"] == "b"
