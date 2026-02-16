from __future__ import annotations

from openpyxl.styles import PatternFill
from openpyxl.cell.cell import Cell

CONFIDENCE_COLORS = {
    "high": None,
    "medium": "FFF3CD",
    "low": "FFE5CC",
    "human_only": "FFE5CC",
    "error": "F8D7DA",
}


def apply_confidence_styling(cell: Cell, confidence_level: str) -> None:
    color = CONFIDENCE_COLORS.get(confidence_level)
    if not color:
        return
    cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
