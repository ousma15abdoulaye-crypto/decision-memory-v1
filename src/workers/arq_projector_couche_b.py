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

Référence : Plan V4.2.0 Phase 5b — ARQ projector Couche B
"""

from __future__ import annotations

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
    """Crée la table de curseur si elle n'existe pas encore."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {_PROJECTION_LOG_TABLE} (
            id          BIGSERIAL PRIMARY KEY,
            event_id    BIGINT NOT NULL,
            event_type  TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'ok',  -- ok | failed
            error_msg   TEXT,
            projected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)
    conn.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_proj_log_event_id
        ON {_PROJECTION_LOG_TABLE}(event_id)
        """)


def _get_last_projected_event_id(conn) -> int:
    """Retourne le dernier event_id projeté (0 si aucun)."""
    row = conn.execute(
        f"SELECT MAX(event_id) FROM {_PROJECTION_LOG_TABLE} WHERE status = 'ok'"
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _fetch_pending_events(conn, last_id: int, batch: int) -> list[dict]:
    """Lit les workspace_events non encore projetés."""
    rows = conn.execute(
        """
        SELECT id, workspace_id, event_type, actor_id, payload, emitted_at
        FROM workspace_events
        WHERE id > %s
          AND event_type = ANY(%s)
        ORDER BY id ASC
        LIMIT %s
        """,
        (last_id, list(_PROJECTED_EVENT_TYPES), batch),
    ).fetchall()
    keys = ["id", "workspace_id", "event_type", "actor_id", "payload", "emitted_at"]
    return [dict(zip(keys, row)) for row in rows]


def _project_evaluation_sealed(conn, event: dict) -> None:
    """Projette EVALUATION_SEALED → vendor_market_signals.

    Pour chaque ligne de scores dans le payload, insère un signal
    vendor_market_signals afin d'enrichir la mémoire marché.
    """
    payload = event.get("payload") or {}
    workspace_id = event["workspace_id"]
    scores = payload.get("scores", [])

    for score in scores:
        vendor_name = score.get("vendor_name") or score.get("supplier_name")
        item_code = score.get("item_code") or score.get("dict_item_code")
        unit_price = score.get("unit_price")
        currency = score.get("currency", "XOF")

        if not vendor_name or not item_code:
            continue

        conn.execute(
            """
            INSERT INTO vendor_market_signals
                (workspace_id, vendor_name, dict_item_code,
                 signal_type, unit_price, currency, metadata, observed_at)
            VALUES (%s, %s, %s, 'OFFER_PRICE', %s, %s, %s::jsonb, NOW())
            ON CONFLICT DO NOTHING
            """,
            (
                workspace_id,
                vendor_name,
                item_code,
                unit_price,
                currency,
                __import__("json").dumps(score),
            ),
        )
        logger.debug(
            "[PROJ] vendor_market_signals inséré vendor=%s item=%s prix=%s",
            vendor_name,
            item_code,
            unit_price,
        )


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
                VALUES (%s, %s, %s, %s, 'PASS_MINUS_1', NOW())
                ON CONFLICT DO NOTHING
                """,
                (workspace_id, bundle_id, item_code, score),
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                workspace_id,
                actor_id,
                vendor_name,
                field_name,
                str(original) if original is not None else None,
                str(corrected) if corrected is not None else None,
                reason,
            ),
        )
    except Exception as exc:
        logger.debug("[PROJ] m13_correction_log skip : %s", exc)


_PROJECTORS = {
    "EVALUATION_SEALED": _project_evaluation_sealed,
    "BUNDLE_SCORED": _project_bundle_scored,
    "VENDOR_SCORE_CHALLENGED": _project_vendor_score_challenged,
    "WORKSPACE_CLOSED": lambda conn, ev: None,  # no-op, logged only
}


async def project_workspace_events_to_couche_b(ctx: dict[str, Any]) -> dict:
    """Task ARQ — projette les workspace_events non traités vers Couche B.

    Idempotent. Traite au plus _BATCH_SIZE events par appel.
    Retourne un résumé {ok, failed, last_event_id}.

    INV-PROJ-01 : Zéro écriture dans process_workspaces.
    INV-PROJ-02 : arq_projection_log assure l'idempotence.
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
                    VALUES (%s, %s, 'ok')
                    """,
                    (event_id, event_type),
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
                        VALUES (%s, %s, 'failed', %s)
                        """,
                        (event_id, event_type, str(exc)[:500]),
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
