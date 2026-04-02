"""Charge document_validity_rules.yaml vers RegulatoryDocumentValidityRule."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.procurement.compliance_models_m13 import (
    NormativeReference,
    RegulatoryDocumentValidityRule,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REG_ROOT = _REPO_ROOT / "config" / "regulatory"


class RegulatoryYamlValidityLoader:
    def __init__(self, base_path: Path | None = None) -> None:
        self.base = base_path or _REG_ROOT

    def load(self, framework: str) -> list[RegulatoryDocumentValidityRule]:
        path = self.base / framework / "document_validity_rules.yaml"
        if not path.is_file():
            return []
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        fw = raw.get("framework", framework)
        rules: list[RegulatoryDocumentValidityRule] = []
        for subtype, rule_data in (raw.get("rules") or {}).items():
            rules.append(
                RegulatoryDocumentValidityRule(
                    framework=fw,
                    admin_subtype=subtype,
                    document_name=rule_data["document_name"],
                    validity_period_months=rule_data.get("validity_period_months"),
                    validity_period_days=rule_data.get("validity_period_days"),
                    no_expiry=rule_data.get("no_expiry", False),
                    validity_from=rule_data.get("validity_from", "issue_date"),
                    validity_note=rule_data.get("validity_note", ""),
                    expiry_consequence=rule_data["expiry_consequence"],
                    grace_period_days=rule_data.get("grace_period_days", 0),
                    renewal_instruction=rule_data.get("renewal_instruction", ""),
                    renewal_typical_duration_days=rule_data.get(
                        "renewal_typical_duration_days"
                    ),
                    normative_reference=NormativeReference(
                        framework=fw,
                        article=rule_data.get("article"),
                        description=rule_data.get(
                            "reference",
                            f"{fw} validity rule",
                        ),
                    ),
                )
            )
        return rules
