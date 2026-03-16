"""
DETTE-8 — Compute signaux IMC → market_signals_v2
Enrichissement des signaux marché avec indices INSTAT.

Architecture IMC figée (Context Anchor 2026-03-15) :
  SOURCE-1 mercurials   : prix DGMP zone×item
  SOURCE-2 imc_entries  : indices INSTAT catégorie×mois
  Pont     imc_category_item_map : category_raw → item_id

Formule révision : P1 = P0 × (IMC_t1 / IMC_t0)

RÈGLE-09 : zéro recommendation / winner / rank / offer_preference
RÈGLE-22 : formule versionnée — formula_version tracée
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import psycopg
from psycopg.rows import dict_row

from src.couche_b.imc_map import compute_price_revision

logger = logging.getLogger(__name__)

# Version formule IMC — versionnée et tracée
IMC_SIGNAL_VERSION = "imc_1.0"

# Seuils signaux IMC (Architecture IMC figée)
IMC_WATCH_MOM = 3.0  # MOM > 3%  → WATCH construction
IMC_STRONG_MOM = 8.0  # MOM > 8%  → STRONG construction
IMC_CRITICAL_YOY = 15.0  # YOY > 15% → CRITICAL construction


# ─────────────────────────────────────────────────────────
# LECTURE — DONNÉES IMC POUR UN ITEM
# ─────────────────────────────────────────────────────────


def get_latest_imc_for_item(
    conn: psycopg.Connection,
    item_id: str,
) -> dict | None:
    """
    Retourne l'indice IMC le plus récent pour un item.
    Chemin : item_id → imc_category_item_map → imc_entries
    Jointure sur LOWER(TRIM(category_raw)) — index fonctionnel 046b.
    Retourne None si aucun mapping disponible.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                e.index_value,
                e.period_year      AS year,
                e.period_month     AS month,
                e.category_raw,
                e.variation_mom,
                e.variation_yoy,
                m.confidence       AS mapping_confidence,
                m.mapping_method
            FROM imc_category_item_map m
            JOIN imc_entries e
              ON LOWER(TRIM(e.category_raw))
               = LOWER(TRIM(m.category_raw))
            WHERE m.item_id = %s
            ORDER BY e.period_year DESC, e.period_month DESC
            LIMIT 1;
            """,
            (item_id,),
        )
        return cur.fetchone()


def get_baseline_imc_for_item(
    conn: psycopg.Connection,
    item_id: str,
    baseline_year: int,
    baseline_month: int,
) -> dict | None:
    """
    Retourne l'indice IMC de référence (baseline) pour un item
    à une période donnée.
    Utilisé comme IMC_t0 dans la formule de révision.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                e.index_value,
                e.period_year  AS year,
                e.period_month AS month,
                e.category_raw
            FROM imc_category_item_map m
            JOIN imc_entries e
              ON LOWER(TRIM(e.category_raw))
               = LOWER(TRIM(m.category_raw))
            WHERE m.item_id      = %s
              AND e.period_year  = %s
              AND e.period_month = %s
            ORDER BY m.confidence DESC
            LIMIT 1;
            """,
            (item_id, baseline_year, baseline_month),
        )
        return cur.fetchone()


# ─────────────────────────────────────────────────────────
# CLASSIFICATION SIGNAL IMC
# ─────────────────────────────────────────────────────────


def classify_imc_signal(
    variation_mom: float | None,
    variation_yoy: float | None,
) -> str:
    """
    Classe le signal IMC selon l'architecture IMC figée.

    Seuils construction (Context Anchor) :
      MOM > 3%  → WATCH
      MOM > 8%  → STRONG
      YOY > 15% → CRITICAL

    Seuils identiques pour toutes les familles.
    Retourne : CRITICAL / STRONG / WATCH / STABLE / UNKNOWN
    """
    if variation_mom is None and variation_yoy is None:
        return "UNKNOWN"

    mom = float(variation_mom) if variation_mom is not None else 0.0
    yoy = float(variation_yoy) if variation_yoy is not None else 0.0

    if yoy > IMC_CRITICAL_YOY:
        return "CRITICAL"
    if mom > IMC_STRONG_MOM:
        return "STRONG"
    if mom > IMC_WATCH_MOM:
        return "WATCH"
    return "STABLE"


# ─────────────────────────────────────────────────────────
# COMPUTE — SIGNAL IMC POUR UN ITEM×SIGNAL
# ─────────────────────────────────────────────────────────


def compute_imc_enrichment(
    conn: psycopg.Connection,
    signal_id: str,
    item_id: str,
    price_avg: float | None,
    baseline_year: int = 2023,
    baseline_month: int = 1,
) -> dict:
    """
    Calcule l'enrichissement IMC pour un signal marché.

    Retourne un dict avec :
      imc_revision_applied : bool
      imc_revision_factor  : float | None
      revised_price_avg    : float | None
      imc_signal_class     : str
      imc_source           : dict (metadata)
      error                : str | None

    RÈGLE-09 : zéro recommendation dans le résultat.
    """
    # Récupérer IMC le plus récent (t1)
    imc_latest = get_latest_imc_for_item(conn, item_id)
    if not imc_latest:
        logger.debug("Aucun mapping IMC pour item_id=%s — skip", item_id)
        return {
            "imc_revision_applied": False,
            "imc_revision_factor": None,
            "revised_price_avg": None,
            "imc_signal_class": "UNKNOWN",
            "imc_source": {"signal_id": signal_id, "reason": "no_imc_mapping"},
            "error": "no_imc_mapping",
        }

    # Récupérer IMC baseline (t0)
    imc_baseline = get_baseline_imc_for_item(
        conn, item_id, baseline_year, baseline_month
    )
    if not imc_baseline:
        logger.debug(
            "Pas de baseline IMC %s/%s pour item_id=%s",
            baseline_year,
            baseline_month,
            item_id,
        )
        return {
            "imc_revision_applied": False,
            "imc_revision_factor": None,
            "revised_price_avg": None,
            "imc_signal_class": classify_imc_signal(
                imc_latest.get("variation_mom"),
                imc_latest.get("variation_yoy"),
            ),
            "imc_source": {
                "signal_id": signal_id,
                "reason": "no_baseline",
                "imc_t1_year": imc_latest["year"],
                "imc_t1_month": imc_latest["month"],
                "category_raw": imc_latest["category_raw"],
            },
            "error": "no_baseline",
        }

    # Calcul révision prix si price_avg disponible
    revision = {"error": "no_price_avg", "revised_price": None}
    if price_avg is not None and price_avg > 0:
        revision = compute_price_revision(
            base_price=float(price_avg),
            imc_t0=float(imc_baseline["index_value"]),
            imc_t1=float(imc_latest["index_value"]),
        )

    imc_class = classify_imc_signal(
        imc_latest.get("variation_mom"),
        imc_latest.get("variation_yoy"),
    )

    applied = (
        revision.get("error") is None and revision.get("revised_price") is not None
    )

    return {
        "imc_revision_applied": applied,
        "imc_revision_factor": revision.get("revision_factor"),
        "revised_price_avg": revision.get("revised_price"),
        "imc_signal_class": imc_class,
        "imc_source": {
            "signal_id": signal_id,
            "category_raw": imc_latest["category_raw"],
            "imc_t0_year": imc_baseline["year"],
            "imc_t0_month": imc_baseline["month"],
            "imc_t0_value": float(imc_baseline["index_value"]),
            "imc_t1_year": imc_latest["year"],
            "imc_t1_month": imc_latest["month"],
            "imc_t1_value": float(imc_latest["index_value"]),
            "mapping_confidence": imc_latest.get("mapping_confidence"),
            "mapping_method": imc_latest.get("mapping_method"),
            "variation_mom": (
                float(imc_latest["variation_mom"])
                if imc_latest.get("variation_mom") is not None
                else None
            ),
            "variation_yoy": (
                float(imc_latest["variation_yoy"])
                if imc_latest.get("variation_yoy") is not None
                else None
            ),
            "formula_version": IMC_SIGNAL_VERSION,
        },
        "error": revision.get("error"),
    }


# ─────────────────────────────────────────────────────────
# BATCH — ENRICHISSEMENT market_signals_v2
# ─────────────────────────────────────────────────────────


def get_signals_pending_imc(
    conn: psycopg.Connection,
    limit: int = 500,
) -> list[dict]:
    """
    Retourne les signaux market_signals_v2 non encore enrichis IMC.
    Filtre : imc_revision_applied = FALSE.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                s.id          AS signal_id,
                s.item_id,
                s.zone_id,
                s.price_avg,
                s.formula_version,
                s.signal_quality,
                s.created_at
            FROM public.market_signals_v2 s
            WHERE s.imc_revision_applied = FALSE
              AND s.price_avg IS NOT NULL
            ORDER BY s.created_at DESC
            LIMIT %s;
            """,
            (limit,),
        )
        return cur.fetchall()


def apply_imc_enrichment_to_signal(
    conn: psycopg.Connection,
    signal_id: str,
    enrichment: dict,
) -> bool:
    """
    Met à jour market_signals_v2 avec les données IMC calculées.
    Retourne True si mise à jour effectuée, False sinon.

    RÈGLE-04 : PostgreSQL = source de vérité.
    Zéro recommendation dans les champs mis à jour.
    """
    if not enrichment.get("imc_revision_applied"):
        logger.debug(
            "Signal %s — IMC non applicable : %s",
            signal_id,
            enrichment.get("error"),
        )
        return False

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.market_signals_v2
            SET
                imc_revision_applied = TRUE,
                imc_revision_factor  = %s,
                imc_revision_at      = %s
            WHERE id = %s
              AND imc_revision_applied = FALSE;
            """,
            (
                enrichment.get("imc_revision_factor"),
                datetime.now(UTC),
                signal_id,
            ),
        )
        updated = cur.rowcount
    conn.commit()

    if updated:
        logger.info(
            "Signal %s enrichi IMC — factor=%.4f class=%s",
            signal_id,
            enrichment.get("imc_revision_factor") or 0,
            enrichment.get("imc_signal_class"),
        )
    return bool(updated)


def run_imc_enrichment_batch(
    conn: psycopg.Connection,
    baseline_year: int = 2023,
    baseline_month: int = 1,
    limit: int = 500,
) -> dict:
    """
    Lance le batch d'enrichissement IMC sur market_signals_v2.

    Retourne les métriques du batch :
      total_processed  : signaux traités
      total_enriched   : signaux mis à jour avec IMC
      total_skipped    : signaux sans mapping IMC
      total_no_baseline: signaux sans baseline IMC
      errors           : liste des erreurs rencontrées

    RÈGLE-09 : zéro recommendation dans les métriques.
    RÈGLE-22 : formula_version tracée.
    """
    signals = get_signals_pending_imc(conn, limit=limit)

    metrics = {
        "total_processed": 0,
        "total_enriched": 0,
        "total_skipped": 0,
        "total_no_baseline": 0,
        "errors": [],
        "baseline_year": baseline_year,
        "baseline_month": baseline_month,
        "formula_version": IMC_SIGNAL_VERSION,
        "ran_at": datetime.now(UTC).isoformat(),
    }

    for signal in signals:
        metrics["total_processed"] += 1
        signal_id = str(signal["signal_id"])
        item_id = str(signal["item_id"])

        try:
            enrichment = compute_imc_enrichment(
                conn=conn,
                signal_id=signal_id,
                item_id=item_id,
                price_avg=(
                    float(signal["price_avg"])
                    if signal.get("price_avg") is not None
                    else None
                ),
                baseline_year=baseline_year,
                baseline_month=baseline_month,
            )

            error = enrichment.get("error")

            if error == "no_imc_mapping":
                metrics["total_skipped"] += 1
                continue

            if error == "no_baseline":
                metrics["total_no_baseline"] += 1
                continue

            updated = apply_imc_enrichment_to_signal(conn, signal_id, enrichment)
            if updated:
                metrics["total_enriched"] += 1
            else:
                metrics["total_skipped"] += 1

        except Exception as exc:
            conn.rollback()
            logger.error(
                "Erreur enrichissement signal %s : %s",
                signal_id,
                exc,
            )
            metrics["errors"].append(
                {
                    "signal_id": signal_id,
                    "error": str(exc),
                }
            )

    logger.info(
        "[IMC BATCH] processed=%d enriched=%d skipped=%d " "no_baseline=%d errors=%d",
        metrics["total_processed"],
        metrics["total_enriched"],
        metrics["total_skipped"],
        metrics["total_no_baseline"],
        len(metrics["errors"]),
    )

    return metrics


# ─────────────────────────────────────────────────────────
# STATS — COUVERTURE IMC
# ─────────────────────────────────────────────────────────


def get_imc_coverage_stats(conn: psycopg.Connection) -> dict:
    """
    Métriques de couverture IMC sur market_signals_v2.
    Utilisé pour rapport M12.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                COUNT(*)                                          AS total_signals,
                SUM(CASE WHEN imc_revision_applied = TRUE
                         THEN 1 ELSE 0 END)                      AS enriched,
                SUM(CASE WHEN imc_revision_applied = FALSE
                         THEN 1 ELSE 0 END)                      AS pending,
                AVG(CASE WHEN imc_revision_applied = TRUE
                         THEN imc_revision_factor END)           AS avg_factor,
                MIN(imc_revision_at)                             AS first_enriched_at,
                MAX(imc_revision_at)                             AS last_enriched_at
            FROM public.market_signals_v2;
            """)
        stats = cur.fetchone() or {}

        return {
            "total_signals": stats.get("total_signals", 0),
            "enriched": stats.get("enriched", 0),
            "pending": stats.get("pending", 0),
            "enrichment_rate": round(
                float(stats.get("enriched") or 0)
                / max(float(stats.get("total_signals") or 1), 1)
                * 100,
                2,
            ),
            "avg_revision_factor": round(float(stats.get("avg_factor") or 1.0), 4),
            "first_enriched_at": str(stats.get("first_enriched_at") or ""),
            "last_enriched_at": str(stats.get("last_enriched_at") or ""),
            "formula_version": IMC_SIGNAL_VERSION,
        }
