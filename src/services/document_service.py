"""Document export service with cryptographic verification."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

from fastapi import HTTPException

from src.db import db_execute_one
from src.utils.json_utils import safe_json_dumps


def _canonical_hash(snapshot: dict[str, Any]) -> str:
    check = deepcopy(snapshot)
    if "seal" in check and isinstance(check["seal"], dict):
        check["seal"].pop("seal_hash", None)
    encoded = safe_json_dumps(check, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def get_sealed_session(conn, workspace_id: str) -> dict[str, Any]:
    """Return sealed snapshot after cryptographic verification.

    - 409 if not sealed
    - 500 if snapshot/hash mismatch
    """
    row = db_execute_one(
        conn,
        """
        SELECT id, session_status, seal_hash, pv_snapshot, sealed_at
        FROM committee_sessions
        WHERE workspace_id = :wid
        """,
        {"wid": workspace_id},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session comité introuvable.")
    if row.get("session_status") != "sealed":
        raise HTTPException(status_code=409, detail="Session non scellée.")
    if not row.get("pv_snapshot") or not row.get("seal_hash"):
        raise HTTPException(status_code=500, detail="Snapshot/Hachage scellé absent.")

    snapshot = row["pv_snapshot"]
    if not isinstance(snapshot, dict):
        raise HTTPException(status_code=500, detail="Snapshot scellé invalide.")

    recomputed = _canonical_hash(snapshot)
    if recomputed != row["seal_hash"]:
        raise HTTPException(
            status_code=500,
            detail="Integrity mismatch: le hash recalculé ne correspond pas au hash scellé.",
        )

    return {
        "session_id": str(row["id"]),
        "sealed_at": row["sealed_at"].isoformat() if row.get("sealed_at") else None,
        "seal_hash": row["seal_hash"],
        "pv_snapshot": snapshot,
    }
