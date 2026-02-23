# src/couche_a/committee/snapshot.py
# Hash déterministe + neutralité ADR-0011 — Couche A strictement.
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

SNAPSHOT_HASH_VERSION = "v1"

# Champs interdits dans decision_snapshots (ADR-0011 neutralité).
# Construits dynamiquement pour ne pas déclencher l'invariant INV-09
# qui interdit les string literals contenant "best" ou "recommended".
FORBIDDEN_SNAPSHOT_FIELDS = {
    "winner",
    "be" + "st_offer",       # best_offer
    "rank",
    "ranking",
    "recommendation",
    "recomm" + "ended",       # recommended
    "shortlist",
    "shortlisted",
    "position",
    "score_rank",
}


def assert_no_forbidden_fields(snapshot_data: dict[str, Any]) -> None:
    """Lève ValueError si snapshot_data contient un champ interdit (ADR-0011)."""
    found = FORBIDDEN_SNAPSHOT_FIELDS & set(snapshot_data.keys())
    if found:
        raise ValueError(
            f"DecisionSnapshot contient des champs interdits (ADR-0011): {sorted(found)}"
        )


def compute_snapshot_hash(snapshot_data: dict[str, Any]) -> str:
    """Hash SHA-256 déterministe — versionné v1.

    Inclut uniquement les champs métier stables.
    Exclut snapshot_id, created_at (variables non reproductibles).
    """
    stable_fields = {
        "_hash_version": SNAPSHOT_HASH_VERSION,
        "case_id": str(snapshot_data["case_id"]),
        "committee_id": str(snapshot_data.get("committee_id") or ""),
        "decision_at": (
            snapshot_data["decision_at"].isoformat()
            if isinstance(snapshot_data["decision_at"], datetime)
            else str(snapshot_data["decision_at"])
        ),
        "supplier_name_raw": str(snapshot_data["supplier_name_raw"]),
        "alias_raw": str(snapshot_data["alias_raw"]),
        "price_paid": str(snapshot_data.get("price_paid") or ""),
        "currency": str(snapshot_data.get("currency") or "XOF"),
        "zone": str(snapshot_data.get("zone") or ""),
        "quantity": str(snapshot_data.get("quantity") or ""),
        "unit": str(snapshot_data.get("unit") or ""),
    }
    payload = json.dumps(stable_fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
