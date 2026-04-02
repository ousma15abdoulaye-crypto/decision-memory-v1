"""
Charge les YAML config/regulatory/{framework}/*.yaml — source unique des seuils M13.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REG_ROOT = _REPO_ROOT / "config" / "regulatory"


class RegulatoryConfigLoader:
    """Loader cache léger pour les fichiers réglementaires par framework."""

    def __init__(self, base_path: Path | None = None) -> None:
        self.base = base_path or _REG_ROOT
        self._cache: dict[str, dict[str, Any]] = {}

    def _framework_dir(self, framework: str) -> Path:
        return self.base / framework

    def load_framework_bundle(self, framework: str) -> dict[str, Any]:
        if framework in self._cache:
            return self._cache[framework]
        d = self.base / framework
        if not d.is_dir():
            logger.warning("[M13] regulatory framework dir missing: %s", d)
            self._cache[framework] = {}
            return {}
        bundle: dict[str, Any] = {}
        for name in (
            "thresholds.yaml",
            "procedure_types.yaml",
            "required_documents.yaml",
            "timelines.yaml",
            "control_organs.yaml",
            "derogations.yaml",
            "principles_mapping.yaml",
        ):
            p = d / name
            if p.is_file():
                try:
                    bundle[name.removesuffix(".yaml")] = yaml.safe_load(
                        p.read_text(encoding="utf-8")
                    )
                except Exception as exc:
                    logger.exception("regulatory yaml load failed %s: %s", p, exc)
                    bundle[name.removesuffix(".yaml")] = {}
            else:
                bundle[name.removesuffix(".yaml")] = {}
        self._cache[framework] = bundle
        return bundle

    def load_derogations(self, framework: str) -> dict[str, Any]:
        return self.load_framework_bundle(framework).get("derogations") or {}

    def get_m13_mode(self) -> str:
        """Mode bootstrap|production depuis env optionnel."""
        import os

        return os.environ.get("M13_MODE", "bootstrap").strip().lower() or "bootstrap"
