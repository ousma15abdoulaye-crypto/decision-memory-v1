"""
Gates minimales DATA-M15 pour exports LS → DMS (JSONL).

Politique : voir docs/mandates/DATA-M15.md — les lignes « annotated_validated »
destinées au corpus M15 doivent passer les contrôles d’export (export_ok).
"""

from __future__ import annotations

from typing import Any


def m15_validated_line_must_export_ok(line: dict[str, Any]) -> str | None:
    """Retourne un message d’erreur si la ligne viole la politique M15, sinon None."""
    ls_meta = line.get("ls_meta") or {}
    status = (ls_meta.get("annotation_status") or "").strip()
    if status != "annotated_validated":
        return None
    if line.get("export_ok") is True:
        return None
    errs = list(line.get("export_errors") or [])
    head = ", ".join(str(e) for e in errs[:5])
    suffix = f"… (+{len(errs) - 5} autres)" if len(errs) > 5 else ""
    return (
        "annotated_validated exige export_ok=true " f"(export_errors: {head}{suffix})"
    )


def collect_m15_gate_violations(lines: list[dict[str, Any]]) -> list[tuple[int, str]]:
    """Indices 0-based des lignes en échec + message (pour CLI ou tests)."""
    out: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        msg = m15_validated_line_must_export_ok(line)
        if msg:
            out.append((i, msg))
    return out
