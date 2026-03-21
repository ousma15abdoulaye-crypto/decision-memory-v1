"""Lecture JSONL M12 pour pipelines aval."""

from __future__ import annotations

import json
from pathlib import Path

from src.annotation.m12_export_io import (
    dms_annotation_from_line,
    export_line_kind,
    iter_m12_jsonl_lines,
    iter_ok_dms_annotations,
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


def test_iter_ok_excludes_raw_dms_lines(tmp_path: Path) -> None:
    p = tmp_path / "raw.jsonl"
    p.write_text(
        json.dumps({"couche_1_routing": {}, "couche_5_gates": []}) + "\n",
        encoding="utf-8",
    )
    assert list(iter_ok_dms_annotations(p, only_export_ok=True)) == []
