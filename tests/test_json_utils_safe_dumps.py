"""Tests — safe_json_dumps (UUID / datetime)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest

from src.utils.json_utils import safe_json_dumps


def test_safe_json_dumps_uuid_and_datetime() -> None:
    uid = uuid.uuid4()
    dt = datetime(2026, 4, 6, 12, 0, 0, tzinfo=UTC)
    s = safe_json_dumps({"id": uid, "at": dt}, sort_keys=True)
    parsed = json.loads(s)
    assert parsed["id"] == str(uid)
    assert parsed["at"] == dt.isoformat()


def test_safe_json_dumps_rejects_custom_default() -> None:
    with pytest.raises(ValueError, match="default"):
        safe_json_dumps({}, default=lambda _: None)
