"""MQL Templates V8 — Canon V5.1.0 Section 8.2.

6 templates SQL paramétrés. INV-A02 : zéro concaténation SQL.
Tous les paramètres sont des bind params (:name style pour psycopg).

Schéma aligné sur ``042_market_surveys`` : ``market_surveys`` (item_id, zone_id,
price_per_unit / price_quoted, supplier_raw, …) et ``survey_campaigns`` (name,
period, start_date, status, org_id) — pas de colonnes ``article_label`` /
``tenant_id`` sur ces tables ; filtre multi-tenant via ``org_id`` (TEXT, UUID
string) lorsque renseigné.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

# Expression prix unitaire effective (trigger 042 ou dérivé quantity)
_MS_UNIT_PRICE = (
    "COALESCE(ms.price_per_unit, ms.price_quoted / NULLIF(ms.quantity_surveyed, 0))"
)

# Filtre zones : libellés extraits de la question (ex. Bamako) vs ``zone_id`` (ex. BKO)
_ZONE_MATCH = """
              EXISTS (
                  SELECT 1
                  FROM unnest(CAST(:zones AS text[])) AS z(pat)
                  WHERE ms.zone_id ILIKE ('%' || pat || '%')
              )
"""

# Périmètre tenant : ``org_id`` optionnel sur les lignes M7 ; si NULL, la ligne reste visible (legacy).
_TENANT_MS = "(ms.org_id IS NULL OR ms.org_id = CAST(:tenant_id AS text))"
_TENANT_SC = "(sc.org_id IS NULL OR sc.org_id = CAST(:tenant_id AS text))"


@dataclass
class MQLParams:
    tenant_id: UUID
    article_pattern: str | None = None
    zones: list[str] | None = None
    vendor_pattern: str | None = None
    min_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    proposed_price: float | None = None
    zone: str | None = None
    max_results: int = 50


MQL_TEMPLATES: dict[str, dict] = {
    "T1_PRICE_MEDIAN": {
        "name": "Prix médian par article et zone",
        "sql": f"""
            SELECT
                ms.item_id AS article_label,
                ms.zone_id AS zone,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {_MS_UNIT_PRICE}) AS median_price,
                MIN({_MS_UNIT_PRICE}) AS min_price,
                MAX({_MS_UNIT_PRICE}) AS max_price,
                COUNT(*) AS sample_count,
                sc.name AS campaign_name,
                COALESCE(sc.period::text, 'unknown') AS source_type,
                COALESCE(sc.org_id, 'unknown') AS publisher,
                sc.start_date::date AS published_date,
                (sc.status = 'active') AS is_official
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE {_TENANT_MS}
              AND {_TENANT_SC}
              AND {_ZONE_MATCH.strip()}
              AND ms.item_id ILIKE :article_pattern
              AND sc.start_date >= :min_date
            GROUP BY ms.item_id, ms.zone_id,
                     sc.name, sc.period, sc.org_id, sc.start_date, sc.status
            ORDER BY sc.start_date DESC
            LIMIT :max_results
        """,
    },
    "T2_PRICE_TREND": {
        "name": "Évolution des prix sur période",
        "sql": f"""
            SELECT
                ms.item_id AS article_label,
                DATE_TRUNC('month', sc.start_date::timestamp) AS period,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {_MS_UNIT_PRICE}) AS median_price,
                COUNT(*) AS sample_count,
                sc.name AS campaign_name,
                COALESCE(sc.period::text, 'unknown') AS source_type,
                COALESCE(sc.org_id, 'unknown') AS publisher,
                sc.start_date::date AS published_date,
                (sc.status = 'active') AS is_official
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE {_TENANT_MS}
              AND {_TENANT_SC}
              AND ms.item_id ILIKE :article_pattern
              AND {_ZONE_MATCH.strip()}
              AND sc.start_date BETWEEN :start_date AND :end_date
            GROUP BY ms.item_id, DATE_TRUNC('month', sc.start_date::timestamp),
                     sc.name, sc.period, sc.org_id, sc.start_date, sc.status
            ORDER BY period ASC
        """,
    },
    "T3_VENDOR_HISTORY": {
        "name": "Historique prix par fournisseur",
        "sql": f"""
            SELECT
                ms.supplier_raw AS vendor_name,
                ms.item_id AS article_label,
                {_MS_UNIT_PRICE} AS unit_price,
                ms.zone_id AS zone,
                sc.name AS campaign_name,
                sc.start_date::date AS published_date,
                COALESCE(sc.period::text, 'unknown') AS source_type,
                (sc.status = 'active') AS is_official
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE {_TENANT_MS}
              AND {_TENANT_SC}
              AND ms.supplier_raw ILIKE :vendor_pattern
              AND sc.start_date >= :min_date
            ORDER BY sc.start_date DESC
            LIMIT :max_results
        """,
    },
    "T4_ZONE_COMPARISON": {
        "name": "Comparaison inter-zones",
        "sql": f"""
            SELECT
                ms.zone_id AS zone,
                ms.item_id AS article_label,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {_MS_UNIT_PRICE}) AS median_price,
                COUNT(DISTINCT ms.supplier_raw) AS vendor_count,
                COUNT(*) AS sample_count,
                sc.name AS campaign_name,
                COALESCE(sc.period::text, 'unknown') AS source_type,
                COALESCE(sc.org_id, 'unknown') AS publisher,
                sc.start_date::date AS published_date,
                (sc.status = 'active') AS is_official
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE {_TENANT_MS}
              AND {_TENANT_SC}
              AND {_ZONE_MATCH.strip()}
              AND ms.item_id ILIKE :article_pattern
              AND sc.start_date >= :min_date
            GROUP BY ms.zone_id, ms.item_id,
                     sc.name, sc.period, sc.org_id, sc.start_date, sc.status
            ORDER BY ms.zone_id
            LIMIT :max_results
        """,
    },
    "T5_ANOMALY_DETECTION": {
        "name": "Détection d'écart de prix",
        "sql": f"""
            WITH stats AS (
                SELECT
                    ms.item_id AS article_label,
                    ms.zone_id AS zone,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {_MS_UNIT_PRICE}) AS median,
                    STDDEV({_MS_UNIT_PRICE}) AS stddev,
                    sc.name AS campaign_name,
                    COALESCE(sc.period::text, 'unknown') AS source_type,
                    COALESCE(sc.org_id, 'unknown') AS publisher,
                    sc.start_date::date AS published_date,
                    (sc.status = 'active') AS is_official
                FROM market_surveys ms
                JOIN survey_campaigns sc ON ms.campaign_id = sc.id
                WHERE {_TENANT_MS}
                  AND {_TENANT_SC}
                  AND sc.start_date >= :min_date
                GROUP BY ms.item_id, ms.zone_id,
                         sc.name, sc.period, sc.org_id, sc.start_date, sc.status
            )
            SELECT
                s.article_label, s.zone, s.median, s.stddev,
                s.campaign_name, s.source_type, s.publisher,
                s.published_date, s.is_official,
                :proposed_price AS proposed_price,
                CASE WHEN s.stddev > 0
                    THEN ROUND(((:proposed_price - s.median) / s.stddev)::numeric, 2)
                    ELSE 0
                END AS z_score,
                ROUND(
                    ((:proposed_price - s.median) / NULLIF(s.median, 0) * 100)::numeric, 1
                ) AS pct_deviation
            FROM stats s
            WHERE s.article_label ILIKE :article_pattern
              AND EXISTS (
                  SELECT 1
                  FROM unnest(CAST(:zones AS text[])) AS z(pat)
                  WHERE s.zone ILIKE ('%' || pat || '%')
              )
        """,
    },
    "T6_CAMPAIGN_INVENTORY": {
        "name": "Inventaire des campagnes disponibles",
        "sql": f"""
            SELECT
                sc.name, COALESCE(sc.period::text, 'unknown') AS source_type,
                COALESCE(sc.org_id, 'unknown') AS publisher,
                sc.start_date::date AS published_date,
                (sc.status = 'active') AS is_official,
                ARRAY(
                    SELECT scz.zone_id FROM survey_campaign_zones scz
                    WHERE scz.campaign_id = sc.id
                ) AS zone_coverage,
                COUNT(ms.id) AS survey_count,
                COUNT(DISTINCT ms.item_id) AS article_count,
                COUNT(DISTINCT ms.supplier_raw) AS vendor_count
            FROM survey_campaigns sc
            LEFT JOIN market_surveys ms ON ms.campaign_id = sc.id
            WHERE {_TENANT_SC}
              AND (
                  :zone::text IS NULL
                  OR EXISTS (
                      SELECT 1 FROM survey_campaign_zones scz
                      WHERE scz.campaign_id = sc.id
                        AND scz.zone_id ILIKE ('%' || :zone::text || '%')
                  )
              )
            GROUP BY sc.id, sc.name, sc.period, sc.org_id, sc.start_date, sc.status
            ORDER BY sc.start_date DESC
        """,
    },
}
