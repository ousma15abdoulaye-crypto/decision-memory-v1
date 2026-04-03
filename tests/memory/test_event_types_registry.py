"""Tests — event_types.yaml registry completeness."""

from __future__ import annotations

from pathlib import Path

import yaml

_REGISTRY_PATH = Path("config/events/event_types.yaml")


class TestEventTypesRegistry:
    def _load(self) -> dict:
        text = _REGISTRY_PATH.read_text(encoding="utf-8")
        return yaml.safe_load(text)

    def test_file_exists(self) -> None:
        assert _REGISTRY_PATH.exists()

    def test_minimum_35_types(self) -> None:
        data = self._load()
        total = sum(len(d.get("events", [])) for d in data.get("domains", {}).values())
        assert total >= 35, f"Expected >= 35 event types, got {total}"

    def test_claimed_total_matches(self) -> None:
        data = self._load()
        total = sum(len(d.get("events", [])) for d in data.get("domains", {}).values())
        assert total == data.get(
            "total_event_types"
        ), f"Claimed {data.get('total_event_types')}, actual {total}"

    def test_all_six_domains_present(self) -> None:
        data = self._load()
        domains = set(data.get("domains", {}).keys())
        expected = {
            "procurement",
            "market",
            "annotation",
            "pipeline",
            "agent",
            "decision",
        }
        assert expected.issubset(domains), f"Missing domains: {expected - domains}"

    def test_no_duplicate_event_names(self) -> None:
        data = self._load()
        seen: set[str] = set()
        dupes: list[str] = []
        for d in data.get("domains", {}).values():
            for e in d.get("events", []):
                if e in seen:
                    dupes.append(e)
                seen.add(e)
        assert dupes == [], f"Duplicate event types: {dupes}"
