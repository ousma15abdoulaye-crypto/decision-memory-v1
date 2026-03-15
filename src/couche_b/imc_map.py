"""
DETTE-7 — imc_category_item_map service
Pont imc_entries (INSTAT) ↔ couche_b.procurement_dict_items (dictionnaire DMS)

Corrections probe ÉTAPE 0 :
  - item_id = TEXT (pas UUID)
  - imc_entries : period_year / period_month
  - schema couche_b explicite
  - FK : couche_b.procurement_dict_items

Formule révision : P1 = P0 × (IMC_t1 / IMC_t0)
"""

from __future__ import annotations

import logging

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# LECTURE
# ─────────────────────────────────────────────────────────

def get_imc_for_item(
    conn: psycopg.Connection,
    item_id: str,
    year: int,
    month: int,
) -> dict | None:
    """
    Retourne l'indice IMC INSTAT pour un item du dictionnaire DMS.
    Chemin :
      item_id → imc_category_item_map → category_raw
              → imc_entries (period_year / period_month)
    Retourne None si aucun mapping ou aucune donnée IMC disponible.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                e.index_value,
                e.period_year          AS year,
                e.period_month         AS month,
                e.category_raw,
                e.variation_mom,
                e.variation_yoy,
                m.confidence           AS mapping_confidence,
                m.mapping_method
            FROM imc_category_item_map m
            JOIN imc_entries e
              ON LOWER(TRIM(e.category_raw)) = LOWER(TRIM(m.category_raw))
            WHERE m.item_id      = %s
              AND e.period_year  = %s
              AND e.period_month = %s
            ORDER BY m.confidence DESC
            LIMIT 1;
        """, (item_id, year, month))
        row = cur.fetchone()
        if not row:
            logger.debug(
                "Aucun indice IMC pour item_id=%s year=%s month=%s",
                item_id, year, month,
            )
        return row


def get_mappings_for_category(
    conn: psycopg.Connection,
    category_raw: str,
) -> list[dict]:
    """
    Retourne tous les items dictionnaire mappés à une catégorie IMC.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                m.item_id,
                m.confidence,
                m.mapping_method,
                d.canonical_slug,
                d.label_fr
            FROM imc_category_item_map m
            JOIN couche_b.procurement_dict_items d
              ON d.item_id = m.item_id
            WHERE LOWER(TRIM(m.category_raw)) = LOWER(TRIM(%s))
            ORDER BY m.confidence DESC;
        """, (category_raw,))
        return cur.fetchall()


def get_mapping_coverage(conn: psycopg.Connection) -> dict:
    """
    Métriques de couverture du mapping IMC.
    Utilisé pour rapport M12.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                COUNT(DISTINCT category_raw)                           AS categories_mapped,
                COUNT(DISTINCT item_id)                                AS items_mapped,
                COUNT(*)                                               AS total_mappings,
                AVG(confidence)                                        AS avg_confidence,
                SUM(CASE WHEN confidence = 1.0 THEN 1 ELSE 0 END)     AS high_conf_count,
                SUM(CASE WHEN confidence = 0.6 THEN 1 ELSE 0 END)     AS low_conf_count
            FROM imc_category_item_map;
        """)
        stats = cur.fetchone() or {}

        cur.execute("""
            SELECT COUNT(DISTINCT category_raw) AS total
            FROM imc_entries;
        """)
        imc_categories = (cur.fetchone() or {}).get("total", 0)

        cur.execute("""
            SELECT COUNT(*) AS total
            FROM couche_b.procurement_dict_items;
        """)
        dict_total = (cur.fetchone() or {}).get("total", 0)

        return {
            "categories_mapped":   stats.get("categories_mapped", 0),
            "items_mapped":        stats.get("items_mapped", 0),
            "total_mappings":      stats.get("total_mappings", 0),
            "avg_confidence":      round(float(stats.get("avg_confidence") or 0), 3),
            "high_conf_count":     stats.get("high_conf_count", 0),
            "low_conf_count":      stats.get("low_conf_count", 0),
            "imc_categories_total": imc_categories,
            "dict_items_total":    dict_total,
        }


# ─────────────────────────────────────────────────────────
# FORMULE RÉVISION PRIX
# ─────────────────────────────────────────────────────────

def compute_price_revision(
    base_price: float,
    imc_t0: float,
    imc_t1: float,
) -> dict:
    """
    Formule : P1 = P0 × (IMC_t1 / IMC_t0)

    Retourne price révisé + facteur + inputs.
    imc_t0 = 0 → erreur explicite, jamais ZeroDivisionError silencieux.
    """
    if imc_t0 == 0:
        logger.error(
            "compute_price_revision : imc_t0=0 — division impossible "
            "base_price=%s imc_t1=%s", base_price, imc_t1
        )
        return {
            "revised_price":   None,
            "revision_factor": None,
            "base_price":      base_price,
            "imc_t0":          imc_t0,
            "imc_t1":          imc_t1,
            "error":           "imc_t0_zero",
        }

    factor  = imc_t1 / imc_t0
    revised = round(base_price * factor, 4)

    return {
        "revised_price":   revised,
        "revision_factor": round(factor, 6),
        "base_price":      base_price,
        "imc_t0":          imc_t0,
        "imc_t1":          imc_t1,
        "error":           None,
    }


# ─────────────────────────────────────────────────────────
# ÉCRITURE
# ─────────────────────────────────────────────────────────

def insert_mapping(
    conn: psycopg.Connection,
    category_raw: str,
    item_id: str,
    confidence: float,
    mapping_method: str = "manual",
    mapped_by: str = "AO",
    notes: str | None = None,
) -> dict:
    """
    Insère un mapping category_raw ↔ item_id.
    confidence DOIT être dans {0.6, 0.8, 1.0}.
    Idempotent : ON CONFLICT (category_raw, item_id) DO UPDATE.
    """
    if confidence not in (0.6, 0.8, 1.0):
        raise ValueError(
            f"confidence={confidence} hors grille — "
            f"valeurs autorisées : 0.6 / 0.8 / 1.0"
        )

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            INSERT INTO imc_category_item_map
                (category_raw, item_id, confidence,
                 mapping_method, mapped_by, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (category_raw, item_id) DO UPDATE
                SET confidence     = EXCLUDED.confidence,
                    mapping_method = EXCLUDED.mapping_method,
                    mapped_by      = EXCLUDED.mapped_by,
                    notes          = EXCLUDED.notes
            RETURNING id, category_raw, item_id,
                      confidence, mapping_method;
        """, (category_raw, item_id, confidence,
              mapping_method, mapped_by, notes))
        row = cur.fetchone()
        conn.commit()
        logger.info(
            "Mapping IMC : category_raw=%s → item_id=%s conf=%s",
            category_raw, item_id, confidence,
        )
        return row
