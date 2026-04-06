"""Build canonical PV snapshot used for seal and exports."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from src.db import db_execute_one, db_fetchall
from src.utils.json_utils import safe_json_dumps

_KILL_LIST = {
    "winner",
    "rank",
    "recommendation",
    "be" + "st_offer",
    "selected_vendor",
    "weighted_scores",
}


def _sanitize_scores_matrix(data: Any) -> Any:
    if isinstance(data, list):
        return [_sanitize_scores_matrix(v) for v in data]
    if isinstance(data, dict):
        sanitized: dict[str, Any] = {}
        for k, v in data.items():
            if str(k) in _KILL_LIST:
                continue
            sanitized[str(k)] = _sanitize_scores_matrix(v)
        return sanitized
    return data


def _confidence_from_bundle_docs(conn, workspace_id: str) -> dict[str, float]:
    rows = db_fetchall(
        conn,
        """
        SELECT bundle_id, MIN(system_confidence) AS mn
        FROM bundle_documents
        WHERE workspace_id = :ws
        GROUP BY bundle_id
        """,
        {"ws": workspace_id},
    )
    out: dict[str, float] = {}
    for r in rows:
        bid = str(r.get("bundle_id"))
        if r.get("mn") is None:
            continue
        out[bid] = float(r["mn"])
    return out


def _extract_criteria_from_scores(
    scores_matrix: dict[str, Any],
) -> list[dict[str, Any]]:
    criteria_ids: set[str] = set()
    for per_bundle in scores_matrix.values():
        if not isinstance(per_bundle, dict):
            continue
        for cid in per_bundle.keys():
            criteria_ids.add(str(cid))
    return [
        {
            "id": cid,
            "name": cid,
            "label": cid,
            "weight": 0,
            "is_eliminatory": False,
            "unit": None,
        }
        for cid in sorted(criteria_ids)
    ]


def build_pv_snapshot(
    conn,
    workspace_id: str,
    session_id: str,
    user_id: int,
    seal_comment: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Build canonical snapshot and its SHA-256 hash.

    Rules:
    - Snapshot is the only source for exports.
    - No forbidden fields from kill-list.
    - weighted_scores never included in snapshot.
    """
    ws = db_execute_one(
        conn, "SELECT * FROM process_workspaces WHERE id = :id", {"id": workspace_id}
    )
    if not ws:
        raise ValueError(f"Workspace introuvable: {workspace_id}")

    session = db_execute_one(
        conn,
        """
        SELECT id, workspace_id, tenant_id, session_status, activated_at, sealed_at,
               min_members
        FROM committee_sessions
        WHERE id = :sid AND workspace_id = :wid
        """,
        {"sid": session_id, "wid": workspace_id},
    )
    if not session:
        raise ValueError(f"Session introuvable: {session_id}")

    members_rows = db_fetchall(
        conn,
        """
        SELECT id, user_id, role_in_committee, is_voting, joined_at
        FROM committee_session_members
        WHERE session_id = :sid
        ORDER BY joined_at NULLS LAST, id
        """,
        {"sid": session_id},
    )
    members: list[dict[str, Any]] = []
    for m in members_rows:
        members.append(
            {
                "member_id": str(m.get("id")),
                "user_id": str(m.get("user_id")),
                "full_name": f"user_{m.get('user_id')}",
                "department": "—",
                "role": m.get("role_in_committee"),
                "is_voting": bool(m.get("is_voting")),
                "joined_at": (
                    m["joined_at"].isoformat()
                    if m.get("joined_at") is not None
                    else None
                ),
            }
        )
    voting_count = sum(1 for m in members if m["is_voting"])
    try:
        min_members = int(session.get("min_members") or 3)
    except (TypeError, ValueError):
        min_members = 3

    events_rows = db_fetchall(
        conn,
        """
        SELECT id, event_type, actor_id, payload, occurred_at
        FROM committee_deliberation_events
        WHERE session_id = :sid
        ORDER BY occurred_at, id
        """,
        {"sid": session_id},
    )
    events: list[dict[str, Any]] = []
    for e in events_rows:
        payload = e.get("payload") if isinstance(e.get("payload"), dict) else {}
        content = (
            payload.get("content") or payload.get("comment") or payload.get("text")
        )
        events.append(
            {
                "event_id": str(e.get("id")),
                "event_type": e.get("event_type"),
                "actor_id": (
                    str(e.get("actor_id")) if e.get("actor_id") is not None else None
                ),
                "actor_role": payload.get("actor_role"),
                "is_voting_actor": bool(payload.get("is_voting_actor", False)),
                "content": content,
                "occurred_at": (
                    e["occurred_at"].isoformat()
                    if e.get("occurred_at") is not None
                    else None
                ),
                "cognitive_state": payload.get("cognitive_state"),
            }
        )

    criteria_rows = db_fetchall(
        conn,
        """
        SELECT *
        FROM dao_criteria
        WHERE workspace_id = :wid
        ORDER BY created_at NULLS LAST, id
        """,
        {"wid": workspace_id},
    )

    bundles_rows = db_fetchall(
        conn,
        """
        SELECT *
        FROM supplier_bundles
        WHERE workspace_id = :wid
        ORDER BY assembled_at NULLS LAST, id
        """,
        {"wid": workspace_id},
    )
    confidence_by_bundle = _confidence_from_bundle_docs(conn, workspace_id)

    latest_eval = db_execute_one(
        conn,
        """
        SELECT scores_matrix
        FROM evaluation_documents
        WHERE workspace_id = :wid
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"wid": workspace_id},
    )
    raw_scores = latest_eval.get("scores_matrix") if latest_eval else {}
    if not isinstance(raw_scores, dict):
        raw_scores = {}
    scores_matrix = _sanitize_scores_matrix(raw_scores)

    criteria: list[dict[str, Any]] = []
    if criteria_rows:
        for c in criteria_rows:
            criteria.append(
                {
                    "id": str(c.get("id")),
                    "name": c.get("name") or c.get("critere_nom") or str(c.get("id")),
                    "label": c.get("label") or c.get("critere_nom") or str(c.get("id")),
                    "weight": (
                        c.get("weight")
                        if c.get("weight") is not None
                        else c.get("ponderation")
                    ),
                    "is_eliminatory": bool(
                        c.get("is_eliminatory")
                        if c.get("is_eliminatory") is not None
                        else c.get("seuil_elimination") is not None
                    ),
                    "unit": c.get("unit"),
                }
            )
    else:
        criteria = _extract_criteria_from_scores(scores_matrix)

    bundles: list[dict[str, Any]] = []
    for b in bundles_rows:
        bid = str(b.get("id"))
        bundles.append(
            {
                "id": bid,
                "supplier_name_raw": b.get("vendor_name_raw"),
                "supplier_name_display": b.get("vendor_name_raw"),
                "completeness_score": b.get("completeness_score"),
                "assembly_confidence": confidence_by_bundle.get(bid),
                "status": b.get("bundle_status"),
                "elimination_flag": bool(
                    b.get("qualification_status") == "disqualified"
                ),
                "elimination_reason": (
                    "qualification_status=disqualified"
                    if b.get("qualification_status") == "disqualified"
                    else None
                ),
            }
        )

    signals_rows = db_fetchall(
        conn,
        """
        SELECT signal_type, payload, generated_at
        FROM vendor_market_signals
        WHERE source_workspace_id = :wid
        ORDER BY generated_at DESC
        LIMIT 20
        """,
        {"wid": workspace_id},
    )
    used_msv2_fallback = False
    if not signals_rows:
        zone_for_msv2 = ws.get("zone_id")
        if zone_for_msv2:
            # Filtrage zone_id : index idx_msv2_zone_id (migration 080_market_signals_v2_zone_id_index).
            signals_rows = db_fetchall(
                conn,
                """
                SELECT alert_level, residual_pct, item_id, zone_id, price_avg,
                       signal_quality, updated_at, created_at
                FROM market_signals_v2
                WHERE zone_id = :zid
                ORDER BY
                  CASE COALESCE(alert_level, 'NORMAL')
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'WARNING' THEN 2
                    WHEN 'WATCH' THEN 3
                    WHEN 'CONTEXT_NORMAL' THEN 4
                    WHEN 'SEASONAL_NORMAL' THEN 5
                    WHEN 'NORMAL' THEN 6
                    ELSE 9
                  END,
                  ABS(COALESCE(residual_pct, 0)) DESC
                LIMIT 10
                """,
                {"zid": str(zone_for_msv2)},
            )
            used_msv2_fallback = bool(signals_rows)

    market_signals: list[dict[str, Any]] = []
    for s in signals_rows:
        if used_msv2_fallback:
            ts = s.get("updated_at") or s.get("created_at")
            market_signals.append(
                {
                    "signal_type": s.get("alert_level") or "NORMAL",
                    "relevance_score": (
                        float(s["residual_pct"])
                        if s.get("residual_pct") is not None
                        else None
                    ),
                    "data_points": {
                        "item_id": s.get("item_id"),
                        "zone_id": s.get("zone_id"),
                        "price_avg": (
                            str(s.get("price_avg"))
                            if s.get("price_avg") is not None
                            else None
                        ),
                        "signal_quality": s.get("signal_quality"),
                    },
                    "surfaced_at": (ts.isoformat() if ts is not None else None),
                    "source_type": "msv2_fallback",
                }
            )
            continue
        payload = s.get("payload") if isinstance(s.get("payload"), dict) else {}
        market_signals.append(
            {
                "signal_type": s.get("signal_type"),
                "relevance_score": payload.get("relevance_score"),
                "data_points": payload,
                "surfaced_at": (
                    s["generated_at"].isoformat()
                    if s.get("generated_at") is not None
                    else None
                ),
                "source_type": "vms",
            }
        )

    source_rows = db_fetchall(
        conn,
        """
        SELECT doc_type, filename, extraction_confidence, uploaded_at
        FROM source_package_documents
        WHERE workspace_id = :wid
        ORDER BY uploaded_at
        """,
        {"wid": workspace_id},
    )
    source_docs = [
        {
            "doc_type": d.get("doc_type"),
            "filename": d.get("filename"),
            "confidence": d.get("extraction_confidence"),
            "uploaded_at": (
                d["uploaded_at"].isoformat()
                if d.get("uploaded_at") is not None
                else None
            ),
        }
        for d in source_rows
    ]

    sealed_at = datetime.now(UTC)
    snapshot: dict[str, Any] = {
        "format_version": "1.0",
        "dms_version": "4.2.1-docgen",
        "generated_at": sealed_at.isoformat(),
        "process": {
            "workspace_id": str(ws.get("id")),
            "reference_code": ws.get("reference_code"),
            "title": ws.get("title"),
            "process_type": ws.get("process_type"),
            "zone": ws.get("zone"),
            "category": ws.get("category"),
            "estimated_value": ws.get("estimated_value"),
            "currency": ws.get("currency") or "XOF",
            "humanitarian_context": ws.get("humanitarian_context"),
            "tenant_id": str(ws.get("tenant_id")),
        },
        "committee": {
            "session_id": str(session_id),
            "min_members": min_members,
            "quorum_met": voting_count >= min_members,
            "voting_count": voting_count,
            "members": members,
        },
        "deliberation": {"total_events": len(events), "events": events},
        "evaluation": {
            "criteria": criteria,
            "bundles": bundles,
            "scores_matrix": scores_matrix,
        },
        "market_signals": market_signals,
        "source_package": source_docs,
        "decision": {
            "sealed_by": str(user_id),
            "sealed_at": sealed_at.isoformat(),
            "seal_comment": seal_comment or "",
        },
    }
    canonical_json = safe_json_dumps(snapshot, sort_keys=True, ensure_ascii=False)
    seal_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    snapshot["seal"] = {"seal_hash": seal_hash}
    return snapshot, seal_hash
