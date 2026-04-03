"""CandidateRuleService — persists candidate rules to public.candidate_rules.

Migration 063 schema:
    rule_id         TEXT NOT NULL UNIQUE
    origin          TEXT NOT NULL
    target_config   TEXT NOT NULL          ← JSON string (dict serialized)
    change_type     TEXT NOT NULL
    change_detail   JSONB NOT NULL         ← JSON object
    status          TEXT DEFAULT 'proposed'

CandidateRuleGenerator emits dicts with:
    target_config: dict  → serialized to JSON string for TEXT column
    change_detail: str   → wrapped in {"description": ...} for JSONB column
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class _ConnectionProtocol(Protocol):
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None: ...

    def fetchone(self) -> dict[str, Any] | None: ...

    def fetchall(self) -> list[dict[str, Any]]: ...


_INSERT_SQL = """
    INSERT INTO public.candidate_rules (
        rule_id, origin, target_config, change_type, change_detail,
        source_field_path, status
    )
    VALUES (
        :rule_id, :origin, :target_config, :change_type,
        CAST(:change_detail AS jsonb),
        :source_field_path, :status
    )
    ON CONFLICT (rule_id) DO NOTHING
    RETURNING rule_id
"""

_COUNT_SQL = """
    SELECT COUNT(*) AS c FROM public.candidate_rules WHERE status = :status
"""


class CandidateRuleService:
    """Persists proposed candidate rules derived from PatternDetector output."""

    def __init__(self, conn_factory: Callable[[], _ConnectionProtocol]) -> None:
        self._conn_factory = conn_factory

    def save(self, rule: dict[str, Any]) -> str | None:
        """Persist one rule dict.

        Handles type coercion:
          - ``target_config`` dict → JSON string (TEXT column)
          - ``change_detail`` str/dict → JSON string cast to JSONB

        Returns ``rule_id`` if inserted, ``None`` if already exists (ON CONFLICT DO NOTHING).
        """
        raw_target = rule.get("target_config", {})
        if isinstance(raw_target, dict):
            target_config = json.dumps(raw_target, ensure_ascii=False)
        else:
            target_config = str(raw_target)

        raw_detail = rule.get("change_detail", "")
        if isinstance(raw_detail, dict):
            change_detail = json.dumps(raw_detail, ensure_ascii=False)
        elif isinstance(raw_detail, str):
            change_detail = json.dumps({"description": raw_detail}, ensure_ascii=False)
        else:
            change_detail = json.dumps(
                {"description": str(raw_detail)}, ensure_ascii=False
            )

        # Extract source_field_path from target_config if present
        source_field_path: str | None = None
        if isinstance(rule.get("target_config"), dict):
            source_field_path = rule["target_config"].get("field_path")

        params: dict[str, Any] = {
            "rule_id": rule["rule_id"],
            "origin": rule.get("origin", "pattern_detector"),
            "target_config": target_config,
            "change_type": rule.get("change_type", "unknown"),
            "change_detail": change_detail,
            "source_field_path": source_field_path,
            "status": rule.get("status", "proposed"),
        }

        conn = self._conn_factory()
        conn.execute(_INSERT_SQL, params)
        row = conn.fetchone()
        return str(row["rule_id"]) if row else None

    def count_by_status(self, status: str = "proposed") -> int:
        conn = self._conn_factory()
        conn.execute(_COUNT_SQL, {"status": status})
        row = conn.fetchone()
        return int(row["c"]) if row else 0
