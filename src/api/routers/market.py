"""Routes W2 — Market Intelligence (V4.2.0).

Routes SANS workspace_id — zone W2 indépendante (INV-R6 adapté) :
  GET  /market/overview              : aperçu global signaux marché
  GET  /market/items/{item_key}/history   : historique prix item
  GET  /market/vendors/{vendor_id}/signals : signaux fournisseur
  GET  /market/watchlist             : liste de surveillance courante
  POST /market/watchlist             : ajouter un item à la watchlist
  PATCH /market/items/{item_key}/annotate : annoter un signal marché

Référence : docs/freeze/DMS_V4.2.0_ADDENDUM.md §VII routes W2
INV-W06 : aucun champ winner/rank/recommendation dans les réponses.
RÈGLE-W01 : tenant_id extrait du JWT uniquement.

Lecture marché agrégée : ``market_signals_v2`` (ADR-V53). Signaux par fournisseur :
``vendor_market_signals`` (projection post-seal / contexte vendeur).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from pydantic import BaseModel

from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.db import db_execute, db_execute_one, db_fetchall, get_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/market", tags=["market-intelligence-v420"])


@router.get("/overview")
def market_overview(
    user: UserClaims = Depends(get_current_user),
    limit: int = 50,
):
    """Aperçu global : signaux marché récents + items à fort drift.

    Zone W2 — accessible sans workspace_id ouvert.
    """
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )

    lim_safe = max(1, min(limit, 200))

    with get_connection() as conn:
        # Colonnes réelles : migration 043_market_signals_v11 (item_id, zone_id, price_avg, …)
        recent_signals = db_fetchall(
            conn,
            """
            SELECT
                ms.item_id AS item_key,
                ms.alert_level AS signal_type,
                ms.price_avg AS unit_price,
                'XOF' AS currency,
                ms.zone_id AS market_zone,
                ms.signal_quality,
                COALESCE(ms.updated_at, ms.created_at) AS collected_at
            FROM market_signals_v2 ms
            ORDER BY COALESCE(ms.updated_at, ms.created_at) DESC
            LIMIT :lim
            """,
            {"lim": lim_safe},
        )

        watchlist = db_fetchall(
            conn,
            """
            SELECT item_type, item_ref, alert_threshold_pct, is_active
            FROM market_watchlist_items
            WHERE tenant_id = :tid AND is_active = TRUE
            LIMIT 20
            """,
            {"tid": tenant_id},
        )

    return {
        "recent_signals": recent_signals,
        "watchlist_active": watchlist,
        "tenant_id": tenant_id,
    }


@router.get("/items/{item_key}/history")
def item_price_history(
    item_key: str,
    user: UserClaims = Depends(get_current_user),
    limit: int = 12,
):
    """Historique des prix pour un item (par item_key, ex: 'riz-25kg-importé').

    Retourne les N derniers signaux triés par date de collecte décroissante.
    """
    if not item_key.strip():
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail="item_key requis."
        )

    lim_safe = max(1, min(limit, 50))

    with get_connection() as conn:
        rows = db_fetchall(
            conn,
            """
            SELECT
                ms.item_id AS item_key,
                ms.alert_level AS signal_type,
                ms.price_avg AS unit_price,
                'XOF' AS currency,
                ms.zone_id AS market_zone,
                ms.signal_quality,
                COALESCE(ms.updated_at, ms.created_at) AS collected_at,
                ms.context_type_at_computation AS source
            FROM market_signals_v2 ms
            WHERE ms.item_id = :key
            ORDER BY COALESCE(ms.updated_at, ms.created_at) DESC
            LIMIT :lim
            """,
            {"key": item_key.strip(), "lim": lim_safe},
        )

    return {"item_key": item_key, "history": rows}


@router.get("/vendors/{vendor_id}/signals")
def vendor_signals(
    vendor_id: str,
    user: UserClaims = Depends(get_current_user),
):
    """Signaux liés à un fournisseur (table ``vendor_market_signals`` — projection ADR-V53).

    Ne remplace pas le prix de référence agrégé M9 (``market_signals_v2``).
    """
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id requis.",
        )

    with get_connection() as conn:
        signals = db_fetchall(
            conn,
            """
            SELECT id, signal_type, payload, generated_at
            FROM vendor_market_signals
            WHERE vendor_id = :vid AND tenant_id = :tid
            ORDER BY generated_at DESC
            LIMIT 50
            """,
            {"vid": vendor_id, "tid": tenant_id},
        )

    return {"vendor_id": vendor_id, "signals": signals}


@router.get("/watchlist")
def get_watchlist(
    user: UserClaims = Depends(get_current_user),
):
    """Retourne la liste de surveillance du tenant courant."""
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail="tenant_id requis."
        )

    with get_connection() as conn:
        items = db_fetchall(
            conn,
            """
            SELECT id, item_type, item_ref, alert_threshold_pct, is_active, created_at
            FROM market_watchlist_items
            WHERE tenant_id = :tid
            ORDER BY created_at DESC
            """,
            {"tid": tenant_id},
        )

    return {"watchlist": items}


class WatchlistItemCreate(BaseModel):
    model_config = {"extra": "forbid"}

    item_type: str
    item_ref: str
    alert_threshold_pct: float | None = None


@router.post("/watchlist", status_code=http_status.HTTP_201_CREATED)
def add_watchlist_item(
    payload: WatchlistItemCreate,
    user: UserClaims = Depends(get_current_user),
):
    """Ajoute un item ou fournisseur à la liste de surveillance."""
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail="tenant_id requis."
        )

    if payload.item_type not in {"item_key", "vendor"}:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="item_type must be 'item_key' or 'vendor'.",
        )

    user_id = int(user.user_id)
    with get_connection() as conn:
        db_execute(
            conn,
            """
            INSERT INTO market_watchlist_items
                (tenant_id, created_by, item_type, item_ref, alert_threshold_pct)
            VALUES (:tid, :uid, :itype, :iref, :thresh)
            """,
            {
                "tid": tenant_id,
                "uid": user_id,
                "itype": payload.item_type,
                "iref": payload.item_ref.strip(),
                "thresh": payload.alert_threshold_pct,
            },
        )

    return {"status": "added", "item_ref": payload.item_ref}


class MarketAnnotation(BaseModel):
    model_config = {"extra": "forbid"}

    annotation: str
    confidence: float = 0.8

    def model_post_init(self, __context) -> None:
        if self.confidence not in {0.6, 0.8, 1.0}:
            raise ValueError("confidence doit être 0.6, 0.8 ou 1.0")


@router.patch("/items/{item_key}/annotate")
def annotate_market_item(
    item_key: str,
    payload: MarketAnnotation,
    user: UserClaims = Depends(get_current_user),
):
    """Annote un item marché (label humain sur la qualité du signal)."""
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id requis.",
        )

    with get_connection() as conn:
        existing = db_execute_one(
            conn,
            "SELECT item_id AS item_key FROM market_signals_v2 WHERE item_id = :key LIMIT 1",
            {"key": item_key},
        )

    if not existing:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"item_key {item_key!r} introuvable.",
        )

    logger.info(
        "[MARKET] Annotation item=%s user=%s tenant=%s annotation=%s conf=%s",
        item_key,
        user.user_id,
        tenant_id,
        payload.annotation[:50],
        payload.confidence,
    )
    return {"item_key": item_key, "status": "annotated"}
