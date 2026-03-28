"""Lecture JSONL M12 pour pipelines aval."""

from __future__ import annotations

import json
from pathlib import Path

from src.annotation.m12_export_io import (
    dms_annotation_from_line,
    export_line_kind,
    iter_m12_jsonl_lines,
    iter_ok_dms_annotations,
    stable_m12_corpus_ids_from_jsonl_paths,
    stable_m12_corpus_line_id,
)


def test_export_line_kind_and_dms(tmp_path: Path) -> None:
    p = tmp_path / "t.jsonl"
    raw = {"couche_1_routing": {}, "couche_5_gates": []}
    p.write_text(json.dumps(raw) + "\n", encoding="utf-8")
    line = next(iter_m12_jsonl_lines(p))
    assert export_line_kind(line) == "raw_dms"
    assert dms_annotation_from_line(line) is line

    v2 = {
        "export_schema_version": "m12-v2",
        "export_ok": True,
        "dms_annotation": {"couche_1_routing": {"x": 1}},
    }
    assert export_line_kind(v2) == "m12-v2"
    assert dms_annotation_from_line(v2) == {"couche_1_routing": {"x": 1}}


def test_iter_ok_dms_skips_failed_export(tmp_path: Path) -> None:
    p = tmp_path / "mix.jsonl"
    p.write_text(
        json.dumps(
            {
                "export_schema_version": "m12-v2",
                "export_ok": False,
                "dms_annotation": {"a": 1},
            }
        )
        + "\n"
        + json.dumps(
            {
                "export_schema_version": "m12-v2",
                "export_ok": True,
                "dms_annotation": {"b": 2},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = list(iter_ok_dms_annotations(p, only_export_ok=True))
    assert len(out) == 1
    assert out[0] == {"b": 2}


def test_stable_m12_corpus_line_id_hash_and_ls_meta() -> None:
    a = {"content_hash": "abc123", "ls_meta": {"task_id": 1, "annotation_id": 2}}
    b = {"content_hash": "abc123", "ls_meta": {"task_id": 9, "annotation_id": 9}}
    assert stable_m12_corpus_line_id(a) == stable_m12_corpus_line_id(b) == "h:abc123"

    c = {
        "content_hash": "unknown",
        "ls_meta": {"project_id": 7, "task_id": 3, "annotation_id": 4},
    }
    assert stable_m12_corpus_line_id(c) == "t:7:3:4"


def test_iter_ok_excludes_raw_dms_lines(tmp_path: Path) -> None:
    p = tmp_path / "raw.jsonl"
    p.write_text(
        json.dumps({"couche_1_routing": {}, "couche_5_gates": []}) + "\n",
        encoding="utf-8",
    )
    assert list(iter_ok_dms_annotations(p, only_export_ok=True)) == []


def test_stable_m12_corpus_ids_from_jsonl_paths_union(tmp_path: Path) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text(
        json.dumps({"content_hash": "x1", "export_schema_version": "m12-v2"}) + "\n",
        encoding="utf-8",
    )
    b.write_text(
        json.dumps({"content_hash": "x2", "export_schema_version": "m12-v2"})
        + "\n"
        + json.dumps({"content_hash": "x1", "export_schema_version": "m12-v2"})
        + "\n",
        encoding="utf-8",
    )
    ids = stable_m12_corpus_ids_from_jsonl_paths([a, b])
    assert ids == {"h:x1", "h:x2"}
