"""Assemblage du payload evaluation-frame (BLOC5) — logique partagée route + matrice."""

from __future__ import annotations

from typing import Any

from src.api.cognitive_helpers import load_cognitive_facts, map_committee_session_row
from src.cognitive.cognitive_state import (
    compute_cognitive_state,
    describe_cognitive_state,
)
from src.cognitive.confidence_envelope import compute_frame_confidence
from src.cognitive.evaluation_frame import (
    build_zones_of_clarification,
    enrich_criteria_with_dao,
    extract_criteria_from_scores_matrix,
    process_market_signals_for_frame,
)
from src.db import db_execute_one, db_fetchall


def build_evaluation_frame_payload(conn: Any, workspace_id: str) -> dict[str, Any]:
    """Construit le dict renvoyé par ``GET …/evaluation-frame`` (hors auth)."""
    ws = db_execute_one(
        conn,
        "SELECT * FROM process_workspaces WHERE id = :id",
        {"id": workspace_id},
    )
    if not ws:
        return {}

    facts = load_cognitive_facts(conn, ws)
    cognitive = compute_cognitive_state(facts)

    sess = db_execute_one(
        conn,
        """
        SELECT id, session_status, activated_at, sealed_at
        FROM committee_sessions
        WHERE workspace_id = :ws
        """,
        {"ws": workspace_id},
    )
    committee_session = map_committee_session_row(sess)

    eval_rows = db_fetchall(
        conn,
        """
        SELECT scores_matrix, created_at
        FROM evaluation_documents
        WHERE workspace_id = :ws
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"ws": workspace_id},
    )
    scores_matrix = (eval_rows[0].get("scores_matrix") if eval_rows else {}) or {}
    for forbidden in (
        "winner",
        "rank",
        "recommendation",
        "be" + "st_offer",
        "selected_vendor",
    ):
        if isinstance(scores_matrix, dict):
            scores_matrix.pop(forbidden, None)

    try:
        elim = db_fetchall(
            conn,
            """
            SELECT id, reason, created_at
            FROM elimination_log
            WHERE workspace_id = :ws
            ORDER BY created_at DESC
            LIMIT 50
            """,
            {"ws": workspace_id},
        )
    except Exception:
        elim = []

    zone_id_frame = ws.get("zone_id")
    raw_signals: list[dict] = []
    if zone_id_frame:
        msv2_rows = db_fetchall(
            conn,
            """
            SELECT id, alert_level, residual_pct, item_id, zone_id, price_avg,
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
            LIMIT 20
            """,
            {"zid": str(zone_id_frame)},
        )
        for row in msv2_rows:
            ts = row.get("updated_at") or row.get("created_at")
            raw_signals.append(
                {
                    "id": row.get("id"),
                    "signal_type": f"msv2_{row.get('alert_level') or 'NORMAL'}",
                    "payload": {
                        "context_match": 1.0,
                        "data_points": 5.0,
                        "threshold_min": 0.0,
                        "item_id": row.get("item_id"),
                        "zone_id": row.get("zone_id"),
                        "price_avg": (
                            str(row.get("price_avg"))
                            if row.get("price_avg") is not None
                            else None
                        ),
                        "signal_quality": row.get("signal_quality"),
                        "residual_pct": (
                            float(row["residual_pct"])
                            if row.get("residual_pct") is not None
                            else None
                        ),
                        "source_table": "market_signals_v2",
                    },
                    "generated_at": ts,
                }
            )
    if not raw_signals:
        raw_signals = db_fetchall(
            conn,
            """
            SELECT id, signal_type, payload, generated_at
            FROM vendor_market_signals
            WHERE source_workspace_id = :ws
            ORDER BY generated_at DESC
            LIMIT 20
            """,
            {"ws": workspace_id},
        )
    tenant_for_frame = str(ws.get("tenant_id") or "")
    if tenant_for_frame:
        market_signals = process_market_signals_for_frame(
            conn, tenant_for_frame, workspace_id, raw_signals
        )
    else:
        market_signals = []

    criteria = extract_criteria_from_scores_matrix(
        scores_matrix if isinstance(scores_matrix, dict) else {}
    )
    dao_crit_rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id, critere_nom, ponderation,
               is_eliminatory, seuil_elimination
        FROM dao_criteria
        WHERE workspace_id = :ws
        ORDER BY created_at NULLS LAST, id
        """,
        {"ws": workspace_id},
    )
    criteria = enrich_criteria_with_dao(criteria, dao_crit_rows)

    sb_rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id, vendor_name_raw
        FROM supplier_bundles
        WHERE workspace_id = :ws
        ORDER BY bundle_index NULLS LAST, id
        """,
        {"ws": workspace_id},
    )
    suppliers = [
        {
            "id": r["id"],
            "name": (r.get("vendor_name_raw") or r["id"] or "")[:500],
        }
        for r in sb_rows
    ]

    dissents = db_fetchall(
        conn,
        """
        SELECT id, event_type, payload, occurred_at
        FROM committee_deliberation_events
        WHERE workspace_id = :ws AND event_type = 'score_challenged'
        ORDER BY occurred_at DESC
        LIMIT 20
        """,
        {"ws": workspace_id},
    )

    try:
        low_b = db_fetchall(
            conn,
            """
            SELECT id, bundle_id, system_confidence
            FROM bundle_documents
            WHERE workspace_id = :ws
              AND system_confidence < 0.5
              AND hitl_validated_at IS NULL
            """,
            {"ws": workspace_id},
        )
    except Exception:
        low_b = []

    bundle_overalls: list[float] = []
    try:
        rows_mn = db_fetchall(
            conn,
            """
            SELECT bundle_id, MIN(system_confidence) AS mn
            FROM bundle_documents
            WHERE workspace_id = :ws
            GROUP BY bundle_id
            """,
            {"ws": workspace_id},
        )
        bundle_overalls = [float(r["mn"]) for r in rows_mn if r.get("mn") is not None]
    except Exception:
        bundle_overalls = []

    data_quality = compute_frame_confidence(bundle_overalls)
    zones_of_clarification = build_zones_of_clarification(dissents, low_b)

    return {
        "workspace_id": workspace_id,
        "cognitive_state": cognitive,
        "cognitive_state_detail": describe_cognitive_state(cognitive),
        "committee_session": committee_session,
        "criteria": criteria,
        "suppliers": suppliers,
        "scores_matrix": scores_matrix,
        "elimination_flags": elim,
        "market_signals": market_signals,
        "dissents": dissents,
        "data_quality_score": data_quality,
        "low_confidence_bundles": low_b,
        "zones_of_clarification": zones_of_clarification,
    }
