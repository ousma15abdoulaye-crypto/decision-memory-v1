from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from openpyxl.utils import get_column_letter


@dataclass(frozen=True)
class SheetColRule:
    start_col_index: int
    width_per_slot: int

def col_letter_from_index(col_index: int) -> str:
    return get_column_letter(col_index)

def supplier_col_index(start_col_index: int, slot_number: int, width_per_slot: int = 1) -> int:
    if slot_number < 1:
        raise ValueError("slot_number must be >= 1")
    return start_col_index + (slot_number - 1) * width_per_slot

def supplier_col_letter(start_col_index: int, slot_number: int, width_per_slot: int = 1) -> str:
    return col_letter_from_index(supplier_col_index(start_col_index, slot_number, width_per_slot))

def commercial_cols(start_col_index: int, slot_number: int) -> Tuple[str, str]:
    # bloc 2 colonnes : prix, total
    price_idx = supplier_col_index(start_col_index, slot_number, width_per_slot=2)
    total_idx = price_idx + 1
    return col_letter_from_index(price_idx), col_letter_from_index(total_idx)
