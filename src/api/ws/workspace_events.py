"""WebSocket — diffusion temps réel des workspace_events (V4.2.0).

Endpoint : ws://host/ws/workspace/{workspace_id}/events

Protocole :
  1. Client se connecte avec JWT en query param (?token=...) uniquement
     (le header Sec-WebSocket-Protocol n'est pas pris en charge)
  2. Handler vérifie JWT + accès workspace
  3. Poll polling sur workspace_events (SELECT WHERE id > last_seen)
  4. Envoi JSON de chaque nouvel event au client
  5. Heartbeat toutes les 10s si pas de nouveaux events

INV-W07 : le handler ne fait QUE diffuser des rows de workspace_events.
          Zéro calcul côté gateway.
Référence : Plan V4.2.0 Phase 5b — WebSocket architecture
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated

from fastapi import HTTPException, Query, WebSocket, WebSocketDisconnect

from src.couche_a.auth.dependencies import UserClaims, get_current_user_from_token
from src.couche_a.auth.workspace_access import require_workspace_access
from src.db import db_fetchall, get_connection

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 2.0
HEARTBEAT_INTERVAL_S = 10.0
MAX_EVENTS_PER_POLL = 50


async def workspace_events_ws(
    websocket: WebSocket,
    workspace_id: str,
    token: Annotated[str | None, Query(alias="token")] = None,
) -> None:
    """Handler WebSocket pour la diffusion des workspace_events.

    Authentification via query param ?token=<JWT>.
    Poll PostgreSQL workspace_events toutes les 2 secondes.
    Envoie chaque nouvel event (id > last_seen) au client.

    INV-W07 : AUCUN calcul dans ce handler — diffusion pure.
    """
    try:
        user: UserClaims = get_current_user_from_token(token or "")
    except RuntimeError as exc:
        logger.error("[WS] configuration serveur workspace=%s : %s", workspace_id, exc)
        await websocket.close(code=1011, reason="Erreur configuration serveur.")
        return
    except ValueError as exc:
        logger.warning("[WS] JWT invalide workspace=%s : %s", workspace_id, exc)
        await websocket.close(code=4401, reason="JWT invalide ou expiré.")
        return
    except Exception as exc:
        logger.warning("[WS] JWT invalide workspace=%s : %s", workspace_id, exc)
        await websocket.close(code=4401, reason="JWT invalide ou expiré.")
        return

    try:
        require_workspace_access(workspace_id, user)
    except HTTPException as exc:
        logger.warning(
            "[WS] Accès refusé workspace=%s user=%s : %s",
            workspace_id,
            user.user_id,
            exc.detail,
        )
        await websocket.close(code=4403, reason="Accès refusé.")
        return
    except Exception as exc:
        logger.warning("[WS] Accès refusé workspace=%s : %s", workspace_id, exc)
        await websocket.close(code=4403, reason="Accès refusé.")
        return

    await websocket.accept()
    logger.info(
        "[WS] Connexion acceptée workspace=%s user=%s", workspace_id, user.user_id
    )

    last_seen_id: int = 0
    last_heartbeat: float = 0.0

    try:
        while True:
            now = asyncio.get_event_loop().time()

            with get_connection() as conn:
                rows = db_fetchall(
                    conn,
                    """
                    SELECT id, workspace_id, event_type, actor_id,
                           actor_type, payload, emitted_at
                    FROM workspace_events
                    WHERE workspace_id = :ws AND id > :last
                    ORDER BY id ASC
                    LIMIT :lim
                    """,
                    {
                        "ws": workspace_id,
                        "last": last_seen_id,
                        "lim": MAX_EVENTS_PER_POLL,
                    },
                )

            if rows:
                for row in rows:
                    payload = {
                        "id": row["id"],
                        "event_type": row["event_type"],
                        "actor_id": row["actor_id"],
                        "actor_type": row["actor_type"],
                        "payload": row.get("payload") or {},
                        "emitted_at": (
                            row["emitted_at"].isoformat()
                            if hasattr(row.get("emitted_at"), "isoformat")
                            else str(row.get("emitted_at", ""))
                        ),
                    }
                    await websocket.send_text(json.dumps(payload))
                    last_seen_id = max(last_seen_id, row["id"])
                last_heartbeat = now

            elif now - last_heartbeat >= HEARTBEAT_INTERVAL_S:
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
                last_heartbeat = now

            await asyncio.sleep(POLL_INTERVAL_S)

    except WebSocketDisconnect:
        logger.info(
            "[WS] Client déconnecté workspace=%s user=%s", workspace_id, user.user_id
        )
    except Exception as exc:
        logger.error("[WS] Erreur workspace=%s : %s", workspace_id, exc)
        try:
            await websocket.close(code=1011, reason=str(exc)[:100])
        except Exception:
            pass
