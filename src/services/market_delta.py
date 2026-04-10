"""Pipe market_delta — Option B (enterprise) : persistance en base (Rupture R3).

Connecte price_line_bundle_values (prix fournisseur) à market_signals_v2
(prix marché M9) et stocke le résultat dans price_line_bundle_values.market_delta_pct.

Architecture Option B :
  ┌─────────────────┐   persist_market_deltas()   ┌──────────────────────────┐
  │ market_signals  │ ─────────────────────────── │ price_line_bundle_values │
  │ _v2             │                             │ .market_delta_pct   (DB) │
  └─────────────────┘                             └──────────────────────────┘
         ↑                                                    ↓
    FormulaV11 M9                                  list_price_bundle_values()
    (immuable)                                     frame route — lecture seule

Déclencheurs du calcul :
  1. Manuelle  : POST /m16/refresh-market-deltas (admin / supply_chain)
  2. Auto      : après création/MAJ d'un price_line_bundle_value (background task)

Stratégie de jointure :
  Zone : process_workspaces.zone_id → market_signals_v2.zone_id (exact match)
  Item : normalize(price_line_comparisons.label) → market_signals_v2.item_id
         Étape 1 : slug exact  (lowercase, espaces/ponctuations → '_')
         Étape 2 : similarity() pg_trgm > 0.55 (typos, variantes)

Prix de référence : market_signals_v2.price_seasonal_adj
  (déjà ajusté crise + saisonnalité par FormulaV11 — immuable ADR-M9-FORMULA-V1.1)

delta_pct = (montant_fournisseur - prix_marché) / prix_marché  (signé)
  Positif  = fournisseur au-dessus du marché
  Négatif  = fournisseur en dessous du marché
  compute_price_signal() utilise abs() en interne pour le seuillage GREEN/YELLOW/BELL.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.db import db_execute, db_execute_one, db_fetchall

logger = logging.getLogger(__name__)

_ITEM_SIMILARITY_THRESHOLD = 0.55


# ── Types ──────────────────────────────────────────────────────────────────────


@dataclass
class MarketDeltaPersistResult:
    """Résultat d'un cycle persist_market_deltas_for_workspace."""

    workspace_id: str
    zone_id: str | None
    total: int = 0
    updated: int = 0
    no_signal: int = 0
    errors: list[str] = field(default_factory=list)


# ── Normalisation label ────────────────────────────────────────────────────────


def _normalize_label(label: str) -> str:
    """Normalise un label article en slug compatible avec market_signals_v2.item_id.

    NFD → ASCII, lowercase, non-alphanumérique → '_', strip underscores bord.
    Exemple : "Stylo Bic (bleu)" → "stylo_bic_bleu"
    """
    nfkd = unicodedata.normalize("NFKD", label)
    ascii_str = nfkd.encode("ascii", errors="ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_str.lower().strip())
    return slug.strip("_")


# ── Lookup marché (SQL) ────────────────────────────────────────────────────────


def _lookup_market_price(conn: Any, item_slug: str, zone_id: str) -> Decimal | None:
    """Cherche le prix de référence dans market_signals_v2.

    Passe 1 : exact slug match (item_id = :slug).
    Passe 2 : similarity pg_trgm > 0.55.
    Retourne price_seasonal_adj du meilleur signal disponible.
    """
    row = db_execute_one(
        conn,
        """
        SELECT price_seasonal_adj
        FROM market_signals_v2
        WHERE zone_id = :zone
          AND signal_quality IN ('strong', 'moderate', 'propagated')
          AND (
              item_id = :slug
              OR (set_limit(0.55) IS NOT NULL AND similarity(item_id, :slug) > 0.55)
          )
        ORDER BY
            CASE WHEN item_id = :slug THEN 0 ELSE 1 END,
            similarity(item_id, :slug) DESC
        LIMIT 1
        """,
        {"zone": zone_id, "slug": item_slug},
    )
    if row and row.get("price_seasonal_adj") is not None:
        try:
            return Decimal(str(row["price_seasonal_adj"]))
        except Exception:
            pass
    return None


# ── Persistance ────────────────────────────────────────────────────────────────


def persist_market_deltas_for_workspace(
    conn: Any, workspace_id: str
) -> MarketDeltaPersistResult:
    """Calcule et persiste market_delta_pct dans price_line_bundle_values.

    Lit les price_line_bundle_values du workspace, résout le signal marché
    correspondant (item × zone), calcule le delta, puis UPDATE en base.

    Idempotent : peut être appelé plusieurs fois sans effet de bord.
    Re-calcule toujours (pas de skip sur computed_at) pour rester cohérent
    avec les mises à jour de market_signals_v2.

    Args:
        conn: Connexion DB synchrone.
        workspace_id: UUID (str) du workspace.

    Returns:
        MarketDeltaPersistResult avec compteurs updated / no_signal / errors.
    """
    result = MarketDeltaPersistResult(workspace_id=workspace_id, zone_id=None)

    # ── 1. Zone du workspace ──────────────────────────────────────────────
    ws_row = db_execute_one(
        conn,
        "SELECT zone_id FROM process_workspaces WHERE id = CAST(:ws AS uuid)",
        {"ws": workspace_id},
    )
    zone_id: str | None = (ws_row or {}).get("zone_id")
    result.zone_id = zone_id

    if not zone_id:
        logger.info(
            "[MARKET-DELTA] workspace=%s sans zone_id — delta non calculable",
            workspace_id,
        )
        return result

    # ── 2. Lignes prix du workspace ───────────────────────────────────────
    rows = db_fetchall(
        conn,
        """
        SELECT
            plbv.id::text  AS value_id,
            plbv.amount    AS amount,
            plc.label      AS label
        FROM price_line_bundle_values plbv
        JOIN price_line_comparisons   plc  ON plc.id = plbv.price_line_id
        WHERE plbv.workspace_id = CAST(:ws AS uuid)
          AND plbv.amount IS NOT NULL
          AND plbv.amount > 0
        ORDER BY plc.line_code, plbv.bundle_id
        """,
        {"ws": workspace_id},
    )

    result.total = len(rows)
    if not rows:
        logger.debug("[MARKET-DELTA] workspace=%s — aucune ligne prix", workspace_id)
        return result

    # ── 3. Calcul + persistance par ligne ─────────────────────────────────
    now = datetime.now(UTC)
    slug_cache: dict[str, Decimal | None] = {}

    for row in rows:
        value_id = str(row["value_id"])
        label = str(row.get("label") or "").strip()
        amount_raw = row.get("amount")

        if not label or amount_raw is None:
            result.no_signal += 1
            continue

        slug = _normalize_label(label)
        if not slug:
            result.no_signal += 1
            continue

        if slug in slug_cache:
            market_price = slug_cache[slug]
        else:
            market_price = _lookup_market_price(conn, slug, zone_id)
            slug_cache[slug] = market_price

        if market_price is None or market_price == 0:
            # Persiste NULL explicitement pour marquer la tentative
            db_execute(
                conn,
                """
                UPDATE price_line_bundle_values
                SET market_delta_pct        = NULL,
                    market_delta_computed_at = :ts
                WHERE id = CAST(:vid AS uuid)
                """,
                {"ts": now, "vid": value_id},
            )
            result.no_signal += 1
            continue

        try:
            supplier_amount = Decimal(str(amount_raw))
            delta = float((supplier_amount - market_price) / market_price)
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            logger.warning(
                "[MARKET-DELTA] Calcul impossible value=%s label=%r: %s",
                value_id,
                label,
                exc,
            )
            result.errors.append(f"{value_id}: {exc}")
            continue

        db_execute(
            conn,
            """
            UPDATE price_line_bundle_values
            SET market_delta_pct        = :delta,
                market_delta_computed_at = :ts
            WHERE id = CAST(:vid AS uuid)
            """,
            {"delta": delta, "ts": now, "vid": value_id},
        )
        result.updated += 1

    logger.info(
        "[MARKET-DELTA] workspace=%s zone=%s — %d/%d mis à jour, %d sans signal",
        workspace_id,
        zone_id,
        result.updated,
        result.total,
        result.no_signal,
    )
    return result
