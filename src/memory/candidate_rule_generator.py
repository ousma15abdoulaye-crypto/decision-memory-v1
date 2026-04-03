"""
Turn detected patterns into candidate rules (proposed status, not deployed).
"""

from __future__ import annotations

import hashlib
from typing import Any

from src.memory.pattern_models import DetectedPattern, PatternType


class CandidateRuleGenerator:
    """Builds rule dicts from ``DetectedPattern`` rows."""

    def generate_from_patterns(
        self, patterns: list[DetectedPattern]
    ) -> list[dict[str, Any]]:
        rules: list[dict[str, Any]] = []
        for p in patterns:
            if p.pattern_type != PatternType.correction_cluster:
                continue
            fp = p.field_path or ""
            digest = hashlib.sha256(
                f"{p.pattern_type.value}|{fp}|{p.occurrences}".encode()
            ).hexdigest()[:12]
            rule_id = f"cand_corr_cluster_{digest}"
            rules.append(
                {
                    "rule_id": rule_id,
                    "origin": "pattern_detector",
                    "target_config": {"field_path": p.field_path},
                    "change_type": "correction_cluster",
                    "change_detail": p.description,
                    "status": "proposed",
                }
            )
        return rules
