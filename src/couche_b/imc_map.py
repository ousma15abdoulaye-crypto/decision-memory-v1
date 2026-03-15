"""
DETTE-7 — imc_category_item_map service
Pont imc_entries (INSTAT) ↔ couche_b.procurement_dict_items (dictionnaire DMS)

Fix PR #188 Copilot review :
  - Index fonctionnel LOWER(TRIM) aligné migration 046
  - safe_build_ls_result : .get() + filtre gates invalides (helpers backend)
  - safe_log_parse_failure : metadata uniquement (zéro contenu document)

Formule révision : P1 = P0 × (IMC_t1 / IMC_t0)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

# CORS — restreint via env var (fix point 6 Copilot)
# DEFAULT : Label Studio Railway uniquement
# Jamais ["*"] en production
_CORS_ORIGINS_RAW = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:8080",
)
CORS_ORIGINS: list[str] = [o.strip() for o in _CORS_ORIGINS_RAW.split(",") if o.strip()]


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

    Jointure sur LOWER(TRIM(category_raw)) — index fonctionnel 046.
    Retourne None si aucun mapping ou aucune donnée IMC disponible.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
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
              ON LOWER(TRIM(e.category_raw))
               = LOWER(TRIM(m.category_raw))
            WHERE m.item_id      = %s
              AND e.period_year  = %s
              AND e.period_month = %s
            ORDER BY m.confidence DESC
            LIMIT 1;
            """,
            (item_id, year, month),
        )
        row = cur.fetchone()
        if not row:
            logger.debug(
                "Aucun indice IMC : item_id=%s year=%s month=%s",
                item_id,
                year,
                month,
            )
        return row


def get_mappings_for_category(
    conn: psycopg.Connection,
    category_raw: str,
) -> list[dict]:
    """
    Retourne tous les items dictionnaire mappés à une catégorie IMC.
    Jointure index fonctionnel LOWER(TRIM).
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
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
            """,
            (category_raw,),
        )
        return cur.fetchall()


def get_mapping_coverage(conn: psycopg.Connection) -> dict:
    """
    Métriques de couverture du mapping IMC.
    Utilisé pour rapport M12.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                COUNT(DISTINCT category_raw)
                    AS categories_mapped,
                COUNT(DISTINCT item_id)
                    AS items_mapped,
                COUNT(*)
                    AS total_mappings,
                AVG(confidence)
                    AS avg_confidence,
                SUM(CASE WHEN confidence = 1.0 THEN 1 ELSE 0 END)
                    AS high_conf_count,
                SUM(CASE WHEN confidence = 0.6 THEN 1 ELSE 0 END)
                    AS low_conf_count
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
            "categories_mapped": stats.get("categories_mapped", 0),
            "items_mapped": stats.get("items_mapped", 0),
            "total_mappings": stats.get("total_mappings", 0),
            "avg_confidence": round(float(stats.get("avg_confidence") or 0), 3),
            "high_conf_count": stats.get("high_conf_count", 0),
            "low_conf_count": stats.get("low_conf_count", 0),
            "imc_categories_total": imc_categories,
            "dict_items_total": dict_total,
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
    imc_t0 = 0 → erreur explicite, jamais ZeroDivisionError silencieux.
    """
    if imc_t0 == 0:
        logger.error(
            "compute_price_revision : imc_t0=0 — division impossible "
            "base_price=%s imc_t1=%s",
            base_price,
            imc_t1,
        )
        return {
            "revised_price": None,
            "revision_factor": None,
            "base_price": base_price,
            "imc_t0": imc_t0,
            "imc_t1": imc_t1,
            "error": "imc_t0_zero",
        }

    factor = imc_t1 / imc_t0
    revised = round(base_price * factor, 4)

    return {
        "revised_price": revised,
        "revision_factor": round(factor, 6),
        "base_price": base_price,
        "imc_t0": imc_t0,
        "imc_t1": imc_t1,
        "error": None,
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
        cur.execute(
            """
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
            """,
            (
                category_raw,
                item_id,
                confidence,
                mapping_method,
                mapped_by,
                notes,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        logger.info(
            "Mapping IMC : category_raw=%s → item_id=%s conf=%s",
            category_raw,
            item_id,
            confidence,
        )
        return row


# ─────────────────────────────────────────────────────────
# HELPERS BACKEND (utilisés par backend.py annotation)
# ─────────────────────────────────────────────────────────


def safe_build_ls_result(parsed: dict, task_id: int) -> list[dict]:
    """
    Fix point 3 Copilot — _build_ls_result robuste.
    Utilise .get() sur chaque gate. Filtre les entrées invalides.
    Zéro KeyError si JSON Mistral partiellement conforme.
    """
    routing = parsed.get("couche_1_routing", {})
    meta = parsed.get("_meta", {})
    gates = parsed.get("couche_5_gates", [])
    ambig = parsed.get("ambiguites", [])

    # Filtre défensif : garder uniquement les gates valides
    valid_gates = [g for g in gates if isinstance(g, dict) and "gate_name" in g]

    gates_failed = [
        g.get("gate_name", "unknown")
        for g in valid_gates
        if g.get("gate_value") is False and g.get("gate_state") == "APPLICABLE"
    ]

    family = routing.get("procurement_family_main", "UNKNOWN")
    sub = routing.get("procurement_family_sub", "UNKNOWN")
    tax_core = routing.get("taxonomy_core", "UNKNOWN")
    role = routing.get("document_role", "UNKNOWN")
    stage = routing.get("document_stage", "UNKNOWN")
    review = meta.get("review_required", False)

    notes = (
        f"[v3.0.1a] {family}/{sub}\n"
        f"taxonomy={tax_core} | role={role} | stage={stage}\n"
        f"review_required={review}\n"
        f"gates_failed={gates_failed if gates_failed else 'aucun'}\n"
        f"ambiguites={ambig if ambig else 'aucune'}\n"
        f"model={meta.get('mistral_model_used', '?')}"
    )

    return [
        {
            "from_name": "extracted_json",
            "to_name": "document_text",
            "type": "textarea",
            "value": {"text": [json.dumps(parsed, ensure_ascii=False, indent=2)]},
        },
        {
            "from_name": "annotation_notes",
            "to_name": "document_text",
            "type": "textarea",
            "value": {"text": [notes]},
        },
    ]


def safe_log_parse_failure(raw: str, task_id: int) -> None:
    """
    Fix point 5 Copilot — log fallback sans contenu document.
    Log uniquement : taille, hash court, task_id.
    Zéro raw[:300] en logs.
    """
    raw_len = len(raw) if raw else 0
    raw_hash = hashlib.sha256(raw.encode()).hexdigest()[:12] if raw else "empty"
    logger.error(
        "[PARSE] Fallback activé — task_id=%s raw_len=%s raw_hash=%s",
        task_id,
        raw_len,
        raw_hash,
    )
