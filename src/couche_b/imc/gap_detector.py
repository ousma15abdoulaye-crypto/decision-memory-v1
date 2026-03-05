"""
Détecteur de trous IMC — DA-009.
Trous tracés · jamais interpolés.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Gap:
    year: int
    month: int


def detect_gaps(
    present: list[tuple[int, int]],
    *,
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
) -> list[Gap]:
    """
    Détecte les mois manquants dans la plage [start, end].
    present = [(year, month), ...] des mois ayant des données.
    """
    present_set = set(present)
    gaps: list[Gap] = []

    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        if (y, m) not in present_set:
            gaps.append(Gap(year=y, month=m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    return gaps
