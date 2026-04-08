"""MQL Templates V8 — Canon V5.1.0 Section 8.2.

6 templates SQL paramétrés. INV-A02 : zéro concaténation SQL.
Tous les paramètres sont des bind params (:name style pour psycopg).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID


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
        "sql": """
            SELECT
                ms.article_label,
                ms.zone,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.unit_price) AS median_price,
                MIN(ms.unit_price) AS min_price,
                MAX(ms.unit_price) AS max_price,
                COUNT(*) AS sample_count,
                sc.name AS campaign_name,
                sc.source_type,
                sc.publisher,
                sc.published_date,
                sc.is_official
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE ms.tenant_id = :tenant_id
              AND ms.zone = ANY(:zones)
              AND ms.article_label ILIKE :article_pattern
              AND sc.published_date >= :min_date
            GROUP BY ms.article_label, ms.zone,
                     sc.name, sc.source_type, sc.publisher,
                     sc.published_date, sc.is_official
            ORDER BY sc.published_date DESC
            LIMIT :max_results
        """,
    },
    "T2_PRICE_TREND": {
        "name": "Évolution des prix sur période",
        "sql": """
            SELECT
                ms.article_label,
                DATE_TRUNC('month', sc.published_date) AS period,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.unit_price) AS median_price,
                COUNT(*) AS sample_count,
                sc.name AS campaign_name,
                sc.source_type,
                sc.publisher,
                sc.published_date,
                sc.is_official
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE ms.tenant_id = :tenant_id
              AND ms.article_label ILIKE :article_pattern
              AND ms.zone = ANY(:zones)
              AND sc.published_date BETWEEN :start_date AND :end_date
            GROUP BY ms.article_label, DATE_TRUNC('month', sc.published_date),
                     sc.name, sc.source_type, sc.publisher,
                     sc.published_date, sc.is_official
            ORDER BY period ASC
        """,
    },
    "T3_VENDOR_HISTORY": {
        "name": "Historique prix par fournisseur",
        "sql": """
            SELECT
                ms.vendor_name, ms.article_label, ms.unit_price,
                ms.zone, sc.name AS campaign_name,
                sc.published_date, sc.source_type, sc.is_official
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE ms.tenant_id = :tenant_id
              AND ms.vendor_name ILIKE :vendor_pattern
              AND sc.published_date >= :min_date
            ORDER BY sc.published_date DESC
            LIMIT :max_results
        """,
    },
    "T4_ZONE_COMPARISON": {
        "name": "Comparaison inter-zones",
        "sql": """
            SELECT
                ms.zone, ms.article_label,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.unit_price) AS median_price,
                COUNT(DISTINCT ms.vendor_name) AS vendor_count,
                COUNT(*) AS sample_count,
                sc.name AS campaign_name,
                sc.source_type,
                sc.publisher,
                sc.published_date,
                sc.is_official
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE ms.tenant_id = :tenant_id
              AND ms.zone = ANY(:zones)
              AND ms.article_label ILIKE :article_pattern
              AND sc.published_date >= :min_date
            GROUP BY ms.zone, ms.article_label,
                     sc.name, sc.source_type, sc.publisher,
                     sc.published_date, sc.is_official
            ORDER BY ms.zone
            LIMIT :max_results
        """,
    },
    "T5_ANOMALY_DETECTION": {
        "name": "Détection d'écart de prix",
        "sql": """
            WITH stats AS (
                SELECT
                    ms.article_label, ms.zone,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.unit_price) AS median,
                    STDDEV(ms.unit_price) AS stddev,
                    sc.name AS campaign_name,
                    sc.source_type,
                    sc.publisher,
                    sc.published_date,
                    sc.is_official
                FROM market_surveys ms
                JOIN survey_campaigns sc ON ms.campaign_id = sc.id
                WHERE ms.tenant_id = :tenant_id
                  AND sc.published_date >= :min_date
                GROUP BY ms.article_label, ms.zone,
                         sc.name, sc.source_type, sc.publisher,
                         sc.published_date, sc.is_official
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
              AND s.zone = ANY(:zones)
        """,
    },
    "T6_CAMPAIGN_INVENTORY": {
        "name": "Inventaire des campagnes disponibles",
        "sql": """
            SELECT
                sc.name, sc.source_type, sc.publisher,
                sc.published_date, sc.is_official, sc.zone_coverage,
                COUNT(ms.id) AS survey_count,
                COUNT(DISTINCT ms.article_label) AS article_count,
                COUNT(DISTINCT ms.vendor_name) AS vendor_count
            FROM survey_campaigns sc
            LEFT JOIN market_surveys ms ON ms.campaign_id = sc.id
            WHERE sc.tenant_id = :tenant_id
              AND (:zone IS NULL OR :zone = ANY(sc.zone_coverage))
            GROUP BY sc.id, sc.name, sc.source_type, sc.publisher,
                     sc.published_date, sc.is_official, sc.zone_coverage
            ORDER BY sc.published_date DESC
        """,
    },
}
