"""Loads golden dataset cases for RAGAS evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULT_DIR = Path("data/golden")


class GoldenDatasetLoader:
    """Loads case + expected pairs from golden dataset directory."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or _DEFAULT_DIR

    def load_all(self) -> list[dict[str, Any]]:
        cases_dir = self._base_dir / "cases"
        expected_dir = self._base_dir / "expected"
        if not cases_dir.exists():
            return []
        samples: list[dict[str, Any]] = []
        for case_file in sorted(cases_dir.glob("case_*.json")):
            case_id = case_file.stem
            expected_file = expected_dir / f"{case_id}_expected.json"
            case_data = json.loads(case_file.read_text(encoding="utf-8"))
            expected_data = (
                json.loads(expected_file.read_text(encoding="utf-8"))
                if expected_file.exists()
                else {}
            )
            samples.append({"case": case_data, "expected": expected_data})
        return samples

    def count(self) -> int:
        cases_dir = self._base_dir / "cases"
        if not cases_dir.exists():
            return 0
        return len(list(cases_dir.glob("case_*.json")))
