"""Index reglementaire structure — moteur de regles M13-ready.

Charge les 6 _library.json parses + le mapping declaratif YAML,
et expose une API simple pour interroger les regles applicables.

Usage :
    from src.procurement.regulatory_index import get_regulatory_index

    idx = get_regulatory_index()
    rules = idx.get_applicable_rules("SCI", estimated_value_usd=15000, family="GOODS")
    # -> [RegulatoryRule(rule_id="SCI_5.2_ELIMINATORY_NIF", ...), ...]
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PARSED_DIR = _REPO_ROOT / "data" / "regulatory" / "parsed"
_MAPPINGS_PATH = _REPO_ROOT / "config" / "regulatory_mappings.yaml"


@dataclass(frozen=True)
class RegulatoryRule:
    """Une regle reglementaire indexee."""

    rule_id: str
    source: str
    section: str
    rule_type: str
    description: str
    dms_gate: str | None
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegulatorySource:
    """Metadonnees d'un document reglementaire parse."""

    source_label: str
    title: str
    language: str
    sections_count: int
    text_char_length: int


class RegulatoryIndex:
    """Index central des regles reglementaires DMS."""

    def __init__(self) -> None:
        self._rules: dict[str, RegulatoryRule] = {}
        self._sources: dict[str, RegulatorySource] = {}
        self._load_sources()
        self._load_mappings()

    def _load_sources(self) -> None:
        """Charge les metadonnees des _library.json."""
        if not _PARSED_DIR.is_dir():
            logger.warning(
                "[REG_INDEX] Repertoire %s absent — aucune source chargee", _PARSED_DIR
            )
            return

        for json_file in sorted(_PARSED_DIR.glob("*_library.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                structured = data.get("structured", {})
                label = data.get("source_label_guess", json_file.stem)
                self._sources[label] = RegulatorySource(
                    source_label=label,
                    title=structured.get("title_guess", ""),
                    language=structured.get("language", "fr"),
                    sections_count=len(structured.get("sections", [])),
                    text_char_length=data.get("text_char_length", 0),
                )
                logger.debug(
                    "[REG_INDEX] Source chargee : %s (%d sections)",
                    label,
                    self._sources[label].sections_count,
                )
            except Exception as exc:
                logger.warning(
                    "[REG_INDEX] Erreur chargement %s : %s", json_file.name, exc
                )

    def _load_mappings(self) -> None:
        """Charge le mapping YAML declaratif."""
        if not _MAPPINGS_PATH.is_file():
            logger.warning(
                "[REG_INDEX] Fichier %s absent — aucun mapping charge", _MAPPINGS_PATH
            )
            return

        try:
            import yaml

            data = yaml.safe_load(_MAPPINGS_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                logger.warning("[REG_INDEX] regulatory_mappings.yaml mal forme")
                return

            for rule_data in data.get("rules", []):
                rule = RegulatoryRule(
                    rule_id=rule_data["rule_id"],
                    source=rule_data["source"],
                    section=rule_data.get("section", ""),
                    rule_type=rule_data.get("type", "informational"),
                    description=rule_data.get("description", ""),
                    dms_gate=rule_data.get("dms_gate"),
                    conditions=rule_data.get("conditions", {}),
                )
                self._rules[rule.rule_id] = rule

            logger.info(
                "[REG_INDEX] %d regles chargees depuis %s",
                len(self._rules),
                _MAPPINGS_PATH.name,
            )
        except Exception as exc:
            logger.warning("[REG_INDEX] Erreur chargement YAML : %s", exc)

    @property
    def rules(self) -> dict[str, RegulatoryRule]:
        return dict(self._rules)

    @property
    def sources(self) -> dict[str, RegulatorySource]:
        return dict(self._sources)

    def get_applicable_rules(
        self,
        framework: str,
        estimated_value: float | None = None,
        family: str | None = None,
    ) -> list[RegulatoryRule]:
        """Retourne les regles applicables pour un framework/valeur/famille donnes."""
        applicable: list[RegulatoryRule] = []

        for rule in self._rules.values():
            cond = rule.conditions

            cond_fw = cond.get("framework")
            if cond_fw:
                if isinstance(cond_fw, list):
                    if framework.upper() not in [f.upper() for f in cond_fw]:
                        continue
                elif framework.upper() != str(cond_fw).upper():
                    continue

            if estimated_value is not None:
                min_usd = cond.get("min_value_usd")
                max_usd = cond.get("max_value_usd")
                min_fcfa = cond.get("min_value_fcfa")

                if min_usd is not None and estimated_value < min_usd:
                    continue
                if max_usd is not None and estimated_value > max_usd:
                    continue
                if min_fcfa is not None and estimated_value < min_fcfa:
                    continue

            if family:
                cond_family = cond.get("family")
                if cond_family:
                    if isinstance(cond_family, list):
                        if family.upper() not in [f.upper() for f in cond_family]:
                            continue
                    elif family.upper() != str(cond_family).upper():
                        continue

            applicable.append(rule)

        return applicable

    def get_eliminatory_gates(self, framework: str) -> list[RegulatoryRule]:
        """Retourne les gates eliminatoires pour un framework."""
        return [
            r
            for r in self.get_applicable_rules(framework)
            if r.rule_type == "eliminatory"
        ]

    def get_thresholds(
        self, framework: str, family: str | None = None
    ) -> list[RegulatoryRule]:
        """Retourne les regles de seuil pour un framework/famille."""
        return [
            r
            for r in self.get_applicable_rules(framework, family=family)
            if r.rule_type == "threshold"
        ]


_index_instance: RegulatoryIndex | None = None


def get_regulatory_index() -> RegulatoryIndex:
    """Retourne le singleton RegulatoryIndex."""
    global _index_instance
    if _index_instance is None:
        _index_instance = RegulatoryIndex()
    return _index_instance


def reset_regulatory_index() -> None:
    """Reinitialise le singleton (utile en tests)."""
    global _index_instance
    _index_instance = None
