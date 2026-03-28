"""CLI inventory_m12_corpus_jsonl."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_inventory_json_output(repo_root: Path, tmp_path: Path) -> None:
    p = tmp_path / "c.jsonl"
    line = {
        "export_schema_version": "m12-v2",
        "export_ok": True,
        "content_hash": "abc",
        "ls_meta": {
            "project_id": 1,
            "task_id": 2,
            "annotation_id": 3,
            "annotation_status": "annotated_validated",
        },
    }
    p.write_text(json.dumps(line) + "\n", encoding="utf-8")
    r = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "inventory_m12_corpus_jsonl.py"),
            str(p),
            "--json",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    f0 = data["files"][0]
    assert f0["lines_non_empty"] == 1
    assert f0["unique_stable_ids"] == 1
    assert f0["kinds"]["m12-v2"] == 1
    assert f0["m12_v2_export_ok_true"] == 1


def test_inventory_manifest_tsv(repo_root: Path, tmp_path: Path) -> None:
    p = tmp_path / "x.jsonl"
    line = {
        "export_schema_version": "m12-v2",
        "export_ok": True,
        "content_hash": "zz",
        "ls_meta": {
            "project_id": 9,
            "task_id": 10,
            "annotation_id": 11,
            "annotation_status": "annotated_validated",
        },
    }
    p.write_text(json.dumps(line) + "\n", encoding="utf-8")
    tsv = tmp_path / "m.tsv"
    r = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "inventory_m12_corpus_jsonl.py"),
            str(p),
            "--manifest-tsv",
            str(tsv),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    body = tsv.read_text(encoding="utf-8").strip().splitlines()
    assert len(body) == 2
    assert "annotated_validated" in body[1]
