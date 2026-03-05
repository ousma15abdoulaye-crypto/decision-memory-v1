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
    Retourne le contexte IMC pour un mois donné.
    Si le mois est un trou de série → data_available=False.
    """
    with get_connection() as conn:
        conn.execute(
            """
            SELECT
                e.category_raw,
                e.category_normalized,
                e.index_value,
                e.variation_mom,
                e.variation_yoy
            FROM imc_entries e
            WHERE e.period_year  = %(period_year)s
              AND e.period_month = %(period_month)s
            ORDER BY ABS(COALESCE(e.variation_yoy, 0)) DESC
            """,
            {"period_year": period_year, "period_month": period_month},
        )
        rows = conn.fetchall()

    if not rows:
        return ImcContext(
            period_year=period_year,
            period_month=period_month,
            global_index=None,
            yoy=None,
            mom=None,
            top_movers=[],
            data_available=False,
        )

    values = [float(r["index_value"]) for r in rows if r.get("index_value") is not None]
    global_index = sum(values) / len(values) if values else None

    top_movers = [
        {
            "category": r.get("category_normalized") or r.get("category_raw"),
            "yoy": float(r["variation_yoy"]) if r.get("variation_yoy") else None,
            "mom": float(r["variation_mom"]) if r.get("variation_mom") else None,
        }
        for r in rows[:3]
    ]

    return ImcContext(
        period_year=period_year,
        period_month=period_month,
        global_index=round(global_index, 2) if global_index else None,
        yoy=(
            float(rows[0]["variation_yoy"])
            if rows and rows[0].get("variation_yoy")
            else None
        ),
        mom=(
            float(rows[0]["variation_mom"])
            if rows and rows[0].get("variation_mom")
            else None
        ),
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
    from src.couche_b.imc.gap_detector import Gap, detect_gaps

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
            "index_value": r["index_value"],
            "mom": r["variation_mom"],
            "yoy": r["variation_yoy"],
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
