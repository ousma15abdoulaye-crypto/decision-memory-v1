"""
Interface IMC pour Couche B.
Fonctions déterministes · pas de chatbot · pas de magie.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.db.core import get_connection


@dataclass
class ImcContext:
    """Contexte IMC pour une période donnée."""

    period_year: int
    period_month: int
    global_index: float | None
    yoy: float | None
    mom: float | None
    top_movers: list[dict[str, Any]]
    data_available: bool


@dataclass
class ImcTrend:
    """Série temporelle IMC sur une plage."""

    start_year: int
    start_month: int
    end_year: int
    end_month: int
    series: list[dict[str, Any]]
    gaps: list[dict[str, Any]]


def get_imc_context(
    period_year: int,
    period_month: int,
) -> ImcContext:
    """
    Contexte IMC pour un mois donné.
    global_index / yoy / mom = moyenne agrégée toutes catégories.
    top_movers = 3 catégories avec plus forte variation YoY.
    Les deux sont calculés par requêtes séparées (cohérence garantie).
    data_available = False si trou de série (DA-009).
    """
    with get_connection() as conn:
        conn.execute(
            """
            SELECT
                AVG(index_value)   AS global_index,
                AVG(variation_yoy) AS global_yoy,
                AVG(variation_mom) AS global_mom,
                COUNT(*)           AS nb_categories
            FROM imc_entries
            WHERE period_year  = %(period_year)s
              AND period_month = %(period_month)s
              AND index_value IS NOT NULL
            """,
            {"period_year": period_year, "period_month": period_month},
        )
        global_row = conn.fetchone()

        if not global_row or global_row.get("nb_categories") == 0:
            return ImcContext(
                period_year=period_year,
                period_month=period_month,
                global_index=None,
                yoy=None,
                mom=None,
                top_movers=[],
                data_available=False,
            )

        conn.execute(
            """
            SELECT
                category_normalized,
                category_raw,
                variation_yoy,
                variation_mom
            FROM imc_entries
            WHERE period_year  = %(period_year)s
              AND period_month = %(period_month)s
              AND variation_yoy IS NOT NULL
            ORDER BY ABS(variation_yoy) DESC
            LIMIT 3
            """,
            {"period_year": period_year, "period_month": period_month},
        )
        mover_rows = conn.fetchall()

    top_movers = [
        {
            "category": r.get("category_normalized") or r.get("category_raw"),
            "yoy": (
                float(r["variation_yoy"])
                if r.get("variation_yoy") is not None
                else None
            ),
            "mom": (
                float(r["variation_mom"])
                if r.get("variation_mom") is not None
                else None
            ),
        }
        for r in mover_rows
    ]

    gi = global_row.get("global_index")
    gy = global_row.get("global_yoy")
    gm = global_row.get("global_mom")

    return ImcContext(
        period_year=period_year,
        period_month=period_month,
        global_index=round(float(gi), 2) if gi is not None else None,
        yoy=round(float(gy), 4) if gy is not None else None,
        mom=round(float(gm), 4) if gm is not None else None,
        top_movers=top_movers,
        data_available=True,
    )


def get_imc_trend(
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
) -> ImcTrend:
    """
    Série temporelle IMC sur une plage de dates.
    Les trous sont inclus dans le champ gaps · pas interpolés (DA-009).
    """
    from src.couche_b.imc.gap_detector import detect_gaps

    with get_connection() as conn:
        conn.execute(
            """
            SELECT
                e.period_year,
                e.period_month,
                AVG(e.index_value)::float    AS index_value,
                AVG(e.variation_mom)::float  AS variation_mom,
                AVG(e.variation_yoy)::float  AS variation_yoy
            FROM imc_entries e
            WHERE (e.period_year, e.period_month)
                  BETWEEN (%(start_year)s, %(start_month)s)
                  AND (%(end_year)s, %(end_month)s)
            GROUP BY e.period_year, e.period_month
            ORDER BY e.period_year, e.period_month
            """,
            {
                "start_year": start_year,
                "start_month": start_month,
                "end_year": end_year,
                "end_month": end_month,
            },
        )
        rows = conn.fetchall()

    series = [
        {
            "year": r["period_year"],
            "month": r["period_month"],
            "index_value": (
                float(r["index_value"])
                if r.get("index_value") is not None
                else None
            ),
            "mom": (
                float(r["variation_mom"])
                if r.get("variation_mom") is not None
                else None
            ),
            "yoy": (
                float(r["variation_yoy"])
                if r.get("variation_yoy") is not None
                else None
            ),
        }
        for r in rows
    ]

    present = [(r["period_year"], r["period_month"]) for r in rows]
    gaps = detect_gaps(
        present,
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
    )

    return ImcTrend(
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        series=series,
        gaps=[{"year": g.year, "month": g.month} for g in gaps],
    )
