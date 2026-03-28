"""Filtres export LS — tâches terminées / statut annotation."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ls_export_filters import filter_export_tasks  # noqa: E402


def _ann(
    *,
    aid: int,
    status: str | None = "annotated_validated",
    cancelled: bool = False,
    has_result: bool = True,
) -> dict:
    result = []
    if has_result:
        result = [
            {
                "from_name": "annotation_status",
                "value": {"choices": [status] if status else []},
            },
            {"from_name": "extracted_json", "value": {"text": ["{}"]}},
        ]
    return {
        "id": aid,
        "was_cancelled": cancelled,
        "result": result,
    }


def test_filter_only_finished_drops_cancelled_and_empty_result() -> None:
    tasks = [
        {
            "id": 1,
            "annotations": [
                _ann(aid=10, cancelled=True),
                _ann(aid=11, cancelled=False),
            ],
        },
        {"id": 2, "annotations": [_ann(aid=12, has_result=False)]},
        {"id": 3, "annotations": []},
    ]
    out = filter_export_tasks(tasks, only_finished=True)
    assert len(out) == 1
    assert out[0]["id"] == 1
    assert len(out[0]["annotations"]) == 1
    assert out[0]["annotations"][0]["id"] == 11


def test_filter_only_if_status() -> None:
    tasks = [
        {
            "id": 1,
            "annotations": [
                _ann(aid=1, status="review_required"),
                _ann(aid=2, status="annotated_validated"),
            ],
        }
    ]
    out = filter_export_tasks(
        tasks,
        only_finished=False,
        require_annotation_status="annotated_validated",
    )
    assert len(out) == 1
    assert len(out[0]["annotations"]) == 1
    assert out[0]["annotations"][0]["id"] == 2


def test_no_filter_returns_same_list() -> None:
    tasks = [{"id": 1, "annotations": [_ann(aid=1, cancelled=True)]}]
    out = filter_export_tasks(
        tasks, only_finished=False, require_annotation_status=None
    )
    assert out == tasks
