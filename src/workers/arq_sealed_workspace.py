"""ARQ — projection post-scellement comité (BLOC5 SPEC V4.3.1, C2-V431).

Insère des signaux ``price_anchor_update`` pour chaque bundle ``qualified`` —
indépendamment de ``is_retained``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def project_sealed_workspace(
    ctx: dict[str, Any], workspace_id: str
) -> dict[str, Any]:
    """Tâche ARQ — après COMMIT du seal comité (enqueue depuis committee_sessions)."""

    from src.db import get_connection

    inserted = 0
    with get_connection() as conn:
        conn.execute(
            "SELECT tenant_id FROM process_workspaces WHERE id = :ws",
            {"ws": workspace_id},
        )
        row = conn.fetchone()
        if not row:
            logger.warning("[SEAL-PROJ] workspace %s introuvable", workspace_id)
            return {"workspace_id": workspace_id, "signals": 0}

        tenant_id = str(row["tenant_id"])

        try:
            conn.execute(
                """
                SELECT id, vendor_id, bundle_index, is_retained, qualification_status
                FROM supplier_bundles
                WHERE workspace_id = :ws AND qualification_status = 'qualified'
                """,
                {"ws": workspace_id},
            )
            bundles = conn.fetchall()
        except Exception as exc:
            logger.warning(
                "[SEAL-PROJ] lecture bundles (migration 079 ?): %s — fallback bundle_status",
                exc,
            )
            conn.execute(
                """
                SELECT id, vendor_id, bundle_index, FALSE AS is_retained, 'qualified' AS qualification_status
                FROM supplier_bundles
                WHERE workspace_id = :ws AND bundle_status = 'complete'
                """,
                {"ws": workspace_id},
            )
            bundles = conn.fetchall()

        for b in bundles:
            vid = b.get("vendor_id")
            if not vid:
                logger.debug(
                    "[SEAL-PROJ] bundle %s sans vendor_id — skip signal", b.get("id")
                )
                continue

            payload = json.dumps(
                {
                    "bundle_id": str(b["id"]),
                    "workspace_id": workspace_id,
                    "bundle_index": b.get("bundle_index"),
                    "is_retained": b.get("is_retained"),
                    "bloc5_sealed_projection": True,
                }
            )
            try:
                conn.execute(
                    """
                    INSERT INTO vendor_market_signals
                        (tenant_id, vendor_id, signal_type, payload, source_workspace_id)
                    VALUES (:tid, :vid, 'price_anchor_update', :payload::jsonb, :ws)
                    """,
                    {
                        "tid": tenant_id,
                        "vid": str(vid),
                        "payload": payload,
                        "ws": workspace_id,
                    },
                )
                inserted += 1
                try:
                    conn.execute(
                        """
                        INSERT INTO signal_relevance_log
                            (tenant_id, workspace_id, signal_type, relevance_score, surfaced, payload)
                        VALUES (:tid, :ws, 'price_anchor_update', 1.0, TRUE, :p::jsonb)
                        """,
                        {
                            "tid": tenant_id,
                            "ws": workspace_id,
                            "p": json.dumps(
                                {"bundle_id": str(b["id"]), "note": "sealed_projection"}
                            ),
                        },
                    )
                except Exception:
                    pass
            except Exception as exc:
                logger.debug("[SEAL-PROJ] insert skip: %s", exc)

        elim_inserted = 0
        try:
            conn.execute(
                """
                SELECT el.id AS el_id, el.reason, sb.vendor_id
                FROM elimination_log el
                LEFT JOIN bundle_documents bd
                  ON bd.workspace_id = CAST(:ws AS uuid)
                 AND (
                        bd.id::text = TRIM(el.offer_document_id)
                     OR bd.id = CAST(NULLIF(TRIM(el.offer_document_id), '') AS uuid)
                    )
                LEFT JOIN supplier_bundles sb
                  ON sb.id = bd.bundle_id
                 AND sb.workspace_id = CAST(:ws AS uuid)
                WHERE el.workspace_id = CAST(:ws AS uuid)
                """,
                {"ws": workspace_id},
            )
            elim_rows = conn.fetchall()
        except Exception as exc:
            logger.warning("[SEAL-PROJ] elimination_log: %s", exc)
            elim_rows = []

        for er in elim_rows:
            vid = er.get("vendor_id")
            if not vid:
                logger.debug(
                    "[SEAL-PROJ] elimination %s sans vendor résolu — skip",
                    er.get("el_id"),
                )
                continue
            eid = er.get("el_id")
            reason = (er.get("reason") or "")[:4000]
            payload_el = json.dumps(
                {
                    "elimination_log_id": str(eid),
                    "workspace_id": workspace_id,
                    "reason": reason,
                    "bloc5_elimination_projection": True,
                }
            )
            try:
                conn.execute(
                    """
                    INSERT INTO vendor_market_signals
                        (tenant_id, vendor_id, signal_type, payload, source_workspace_id)
                    VALUES (
                        CAST(:tid AS uuid),
                        CAST(:vid AS uuid),
                        'performance_note',
                        CAST(:payload AS jsonb),
                        CAST(:ws AS uuid)
                    )
                    """,
                    {
                        "tid": tenant_id,
                        "vid": str(vid),
                        "payload": payload_el,
                        "ws": workspace_id,
                    },
                )
                elim_inserted += 1
            except Exception as exc:
                logger.debug("[SEAL-PROJ] elimination insert skip: %s", exc)

    total = inserted + elim_inserted
    logger.info(
        "[SEAL-PROJ] workspace=%s price_anchor=%d elimination=%d total=%d",
        workspace_id,
        inserted,
        elim_inserted,
        total,
    )
    return {
        "workspace_id": workspace_id,
        "signals": total,
        "price_anchor_signals": inserted,
        "elimination_signals": elim_inserted,
    }
