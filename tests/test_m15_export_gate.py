"""Tests gate DATA-M15 (scripts/m15_export_gate.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "m15_export_gate", _ROOT / "scripts" / "m15_export_gate.py"
)
assert _SPEC and _SPEC.loader
_M15 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_M15)

m15_validated_line_must_export_ok = _M15.m15_validated_line_must_export_ok
collect_m15_gate_violations = _M15.collect_m15_gate_violations


def test_validated_with_export_ok_passes() -> None:
    line = {
        "export_ok": True,
        "ls_meta": {"annotation_status": "annotated_validated"},
    }
    assert m15_validated_line_must_export_ok(line) is None


def test_validated_without_export_ok_fails() -> None:
    line = {
        "export_ok": False,
        "export_errors": ["schema_validation:1 errors"],
        "ls_meta": {"annotation_status": "annotated_validated"},
    }
    msg = m15_validated_line_must_export_ok(line)
    assert msg is not None
    assert "export_ok" in msg


def test_draft_ignored_by_gate() -> None:
    line = {
        "export_ok": False,
        "export_errors": ["x"],
        "ls_meta": {"annotation_status": "draft"},
    }
    assert m15_validated_line_must_export_ok(line) is None


def test_collect_m15_gate_violations_indexes() -> None:
    lines = [
        {"export_ok": True, "ls_meta": {"annotation_status": "annotated_validated"}},
        {
            "export_ok": False,
            "export_errors": ["e"],
            "ls_meta": {"annotation_status": "annotated_validated"},
        },
    ]
    v = collect_m15_gate_violations(lines)
    assert len(v) == 1
    assert v[0][0] == 1
    assert "annotated_validated" in v[0][1]
