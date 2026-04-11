"""ARQ Projector — Couche B workspace_events → market memory (V4.2.0).

Responsabilité :
  Consommer les workspace_events de type EVALUATION_SEALED et
  BUNDLE_SCORED afin de mettre à jour les signaux Couche B :
    - vendor_market_signals (nouveau table V4.2.0)
    - mercurial_items / market_signals (tables Couche B existantes)
    - m13_correction_log (pattern learning)

INV-PROJ-01 : Ce projector n'écrit JAMAIS dans process_workspaces.
               Il lit workspace_events (append-only) et écrit Couche B.
INV-PROJ-02 : Idempotent — chaque event ne doit être projeté qu'une fois.
               Table arq_projection_log gère le curseur (event_id traité).
INV-PROJ-03 : En cas d'erreur partielle, l'event est marqué failed
               avec le message d'erreur ; le worker continue.

ADR-V53 : les INSERT ``vendor_market_signals`` sont une **projection mémoire
fournisseur** ; le prix de référence agrégé M9 reste ``market_signals_v2``.

Référence : Plan V4.2.0 Phase 5b — ARQ projector Couche B
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Types d'events projetés vers Couche B
_PROJECTED_EVENT_TYPES = frozenset(
    {
        "EVALUATION_SEALED",
        "BUNDLE_SCORED",
        "VENDOR_SCORE_CHALLENGED",
        "WORKSPACE_CLOSED",
    }
)

_PROJECTION_LOG_TABLE = "arq_projection_log"
_BATCH_SIZE = 100


def _ensure_projection_log(conn) -> None:
    """Crée la table de curseur + contrainte UNIQUE event_id si elle n'existe pas."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {_PROJECTION_LOG_TABLE} (
            id          BIGSERIAL PRIMARY KEY,
            event_id    BIGINT NOT NULL,
            event_type  TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'ok',
            error_msg   TEXT,
            projected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)
    conn.execute(f"""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_proj_log_event_id
        ON {_PROJECTION_LOG_TABLE}(event_id)
        """)
    conn.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_proj_log_event_id
        ON {_PROJECTION_LOG_TABLE}(event_id)
        """)


def _get_last_projected_event_id(conn) -> int:
    """Retourne le dernier event_id projeté avec succès (0 si aucun)."""
    conn.execute(
        f"SELECT MAX(event_id) FROM {_PROJECTION_LOG_TABLE} WHERE status = 'ok'"
    )
    row = conn.fetchone()
    return int(row["max"]) if row and row.get("max") is not None else 0


def _fetch_pending_events(conn, last_id: int, batch: int) -> list[dict]:
    """Lit les workspace_events non encore projetés."""
    conn.execute(
        """
        SELECT id, workspace_id, event_type, actor_id, payload, emitted_at
        FROM workspace_events
        WHERE id > :last_id
          AND event_type = ANY(:event_types)
        ORDER BY id ASC
        LIMIT :lim
        """,
        {"last_id": last_id, "event_types": list(_PROJECTED_EVENT_TYPES), "lim": batch},
    )
    return conn.fetchall()


def _project_evaluation_sealed(conn, event: dict) -> None:
    """Projette EVALUATION_SEALED → vendor_market_signals.

    Insère un signal de type price_anchor_update par ligne de scores.
    Nécessite la résolution de tenant_id (via process_workspaces) et
    vendor_id (via vendors). Si l'un ou l'autre est introuvable, l'insertion
    est silencieusement ignorée — INV-PROJ-03.
    """
    payload = event.get("payload") or {}
    workspace_id = event["workspace_id"]
    scores = payload.get("scores", [])

    conn.execute(
        "SELECT tenant_id FROM process_workspaces WHERE id = :ws",
        {"ws": workspace_id},
    )
    ws_row = conn.fetchone()
    if not ws_row:
        logger.warning(
            "[PROJ] workspace_id=%s introuvable — EVALUATION_SEALED ignoré",
            workspace_id,
        )
        return
    tenant_id = str(ws_row["tenant_id"])

    for score in scores:
        vendor_name = score.get("vendor_name") or score.get("supplier_name")
        if not vendor_name:
            continue

        conn.execute(
            "SELECT id FROM vendors WHERE name = :name LIMIT 1",
            {"name": vendor_name},
        )
        v_row = conn.fetchone()
        if not v_row:
            logger.debug("[PROJ] vendor=%r introuvable — signal ignoré", vendor_name)
            continue
        vendor_id = str(v_row["id"])

        signal_payload = json.dumps(score)
        try:
            conn.execute(
                """
                INSERT INTO vendor_market_signals
                    (tenant_id, vendor_id, signal_type, payload, source_workspace_id)
                VALUES (:tid, :vid, 'price_anchor_update', :payload::jsonb, :ws)
                ON CONFLICT DO NOTHING
                """,
                {
                    "tid": tenant_id,
                    "vid": vendor_id,
                    "payload": signal_payload,
                    "ws": workspace_id,
                },
            )
            logger.debug("[PROJ] vendor_market_signals inséré vendor=%s", vendor_name)
        except Exception as exc:
            logger.debug("[PROJ] vendor_market_signals skip : %s", exc)


def _project_bundle_scored(conn, event: dict) -> None:
    """Projette BUNDLE_SCORED → market_signals (Couche B existante).

    Si la table market_signals n'existe pas encore (déploiement partiel),
    l'erreur est silencieuse — INV-PROJ-03.
    """
    payload = event.get("payload") or {}
    workspace_id = event["workspace_id"]
    bundle_id = payload.get("bundle_id")
    item_scores = payload.get("item_scores", [])

    for item in item_scores:
        item_code = item.get("dict_item_code")
        score = item.get("score")
        if not item_code:
            continue
        try:
            conn.execute(
                """
                INSERT INTO market_signals
                    (workspace_id, bundle_id, dict_item_code, score_value,
                     signal_source, created_at)
                VALUES (:ws, :bid, :code, :score, 'PASS_MINUS_1', NOW())
                ON CONFLICT DO NOTHING
                """,
                {
                    "ws": workspace_id,
                    "bid": bundle_id,
                    "code": item_code,
                    "score": score,
                },
            )
        except Exception as exc:
            logger.debug("[PROJ] market_signals skip (table absente?) : %s", exc)


def _project_vendor_score_challenged(conn, event: dict) -> None:
    """Projette VENDOR_SCORE_CHALLENGED → m13_correction_log."""
    payload = event.get("payload") or {}
    workspace_id = event["workspace_id"]
    actor_id = event.get("actor_id")
    vendor_name = payload.get("vendor_name")
    field_name = payload.get("field_name")
    original = payload.get("original_value")
    corrected = payload.get("corrected_value")
    reason = payload.get("reason", "")

    if not vendor_name or not field_name:
        return

    try:
        conn.execute(
            """
            INSERT INTO m13_correction_log
                (workspace_id, actor_id, vendor_name, field_name,
                 original_value, corrected_value, reason, logged_at)
            VALUES (:ws, :uid, :vendor, :field, :orig, :corr, :reason, NOW())
            """,
            {
                "ws": workspace_id,
                "uid": actor_id,
                "vendor": vendor_name,
                "field": field_name,
                "orig": str(original) if original is not None else None,
                "corr": str(corrected) if corrected is not None else None,
                "reason": reason,
            },
        )
    except Exception as exc:
        logger.debug("[PROJ] m13_correction_log skip : %s", exc)


_PROJECTORS = {
    "EVALUATION_SEALED": _project_evaluation_sealed,
    "BUNDLE_SCORED": _project_bundle_scored,
    "VENDOR_SCORE_CHALLENGED": _project_vendor_score_challenged,
    "WORKSPACE_CLOSED": lambda conn, ev: None,
}


async def project_workspace_events_to_couche_b(ctx: dict[str, Any]) -> dict:
    """Task ARQ — projette les workspace_events non traités vers Couche B.

    Idempotent. Traite au plus _BATCH_SIZE events par appel.
    Retourne un résumé {ok, failed, last_event_id}.

    INV-PROJ-01 : Zéro écriture dans process_workspaces.
    INV-PROJ-02 : arq_projection_log (UNIQUE event_id) assure l'idempotence.
    INV-PROJ-03 : Erreurs partielles → marquées failed, pas de rollback global.
    """
    from src.db import get_connection

    ok_count = 0
    failed_count = 0
    last_id = 0

    with get_connection() as conn:
        _ensure_projection_log(conn)
        last_id = _get_last_projected_event_id(conn)
        events = _fetch_pending_events(conn, last_id, _BATCH_SIZE)

        logger.info("[PROJ] %d events à projeter (depuis id=%d)", len(events), last_id)

        for event in events:
            event_id = event["id"]
            event_type = event["event_type"]
            projector = _PROJECTORS.get(event_type)
            try:
                if projector:
                    projector(conn, event)
                conn.execute(
                    f"""
                    INSERT INTO {_PROJECTION_LOG_TABLE}
                        (event_id, event_type, status)
                    VALUES (:eid, :etype, 'ok')
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    {"eid": event_id, "etype": event_type},
                )
                ok_count += 1
                last_id = event_id
            except Exception as exc:
                logger.error(
                    "[PROJ] Erreur event_id=%d type=%s : %s",
                    event_id,
                    event_type,
                    exc,
                )
                try:
                    conn.execute(
                        f"""
                        INSERT INTO {_PROJECTION_LOG_TABLE}
                            (event_id, event_type, status, error_msg)
                        VALUES (:eid, :etype, 'failed', :err)
                        ON CONFLICT (event_id) DO UPDATE SET
                            status = 'failed', error_msg = EXCLUDED.error_msg
                        """,
                        {"eid": event_id, "etype": event_type, "err": str(exc)[:500]},
                    )
                except Exception:
                    pass
                failed_count += 1

    logger.info(
        "[PROJ] Terminé — ok=%d failed=%d last_event_id=%d",
        ok_count,
        failed_count,
        last_id,
    )
    return {"ok": ok_count, "failed": failed_count, "last_event_id": last_id}
