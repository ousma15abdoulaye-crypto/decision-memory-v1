"""Unit tests for column_calculator module."""
import pytest

from src.mapping.column_calculator import (
    SheetColRule,
    col_letter_from_index,
    commercial_cols,
    supplier_col_index,
    supplier_col_letter,
)


class TestColLetterFromIndex:
    """Tests for col_letter_from_index function."""

    def test_single_letter_columns(self):
        """Column indices 1-26 should return A-Z."""
        assert col_letter_from_index(1) == "A"
        assert col_letter_from_index(2) == "B"
        assert col_letter_from_index(26) == "Z"

    def test_double_letter_columns(self):
        """Column indices beyond 26 should return AA, AB, etc."""
        assert col_letter_from_index(27) == "AA"
        assert col_letter_from_index(28) == "AB"
        assert col_letter_from_index(52) == "AZ"
        assert col_letter_from_index(53) == "BA"

    def test_triple_letter_columns(self):
        """Very high indices should return triple-letter columns."""
        # 26 + 26*26 = 702 is AZ, 703 is BA (after exhausting AA-ZZ which is 702)
        # Actually: A-Z=26, AA-AZ=26, BA-BZ=26, ... ZA-ZZ=26 => AA-ZZ = 26*26 = 676
        # So index 702 = ZZ, 703 = AAA
        assert col_letter_from_index(702) == "ZZ"
        assert col_letter_from_index(703) == "AAA"


class TestSupplierColIndex:
    """Tests for supplier_col_index function."""

    def test_first_slot_returns_start_col(self):
        """Slot 1 should return the start column index."""
        assert supplier_col_index(5, 1, width_per_slot=1) == 5
        assert supplier_col_index(10, 1, width_per_slot=2) == 10

    def test_sequential_slots_width_one(self):
        """Sequential slots with width 1 should increment by 1."""
        assert supplier_col_index(5, 1, width_per_slot=1) == 5
        assert supplier_col_index(5, 2, width_per_slot=1) == 6
        assert supplier_col_index(5, 3, width_per_slot=1) == 7
        assert supplier_col_index(5, 10, width_per_slot=1) == 14

    def test_sequential_slots_width_two(self):
        """Sequential slots with width 2 should increment by 2."""
        assert supplier_col_index(5, 1, width_per_slot=2) == 5
        assert supplier_col_index(5, 2, width_per_slot=2) == 7
        assert supplier_col_index(5, 3, width_per_slot=2) == 9
        assert supplier_col_index(5, 5, width_per_slot=2) == 13

    def test_default_width_is_one(self):
        """Default width_per_slot should be 1."""
        assert supplier_col_index(5, 3) == supplier_col_index(5, 3, width_per_slot=1)

    def test_invalid_slot_raises_error(self):
        """Slot number less than 1 should raise ValueError."""
        with pytest.raises(ValueError, match="slot_number must be >= 1"):
            supplier_col_index(5, 0, 1)
        with pytest.raises(ValueError, match="slot_number must be >= 1"):
            supplier_col_index(5, -1, 1)


class TestSupplierColLetter:
    """Tests for supplier_col_letter function."""

    def test_returns_letter_for_index(self):
        """Should return the correct column letter for the calculated index."""
        # Start at column E (5), slot 1 => E
        assert supplier_col_letter(5, 1, width_per_slot=1) == "E"
        # Start at column E (5), slot 2 => F
        assert supplier_col_letter(5, 2, width_per_slot=1) == "F"

    def test_with_width_two(self):
        """Should correctly calculate letters with width 2."""
        # Start at column F (6), slot 1 => F
        assert supplier_col_letter(6, 1, width_per_slot=2) == "F"
        # Start at column F (6), slot 2 => H (6 + 2 = 8)
        assert supplier_col_letter(6, 2, width_per_slot=2) == "H"

    def test_beyond_single_letter(self):
        """Should handle columns beyond Z."""
        # Start at column Z (26), slot 2 => AA (27)
        assert supplier_col_letter(26, 2, width_per_slot=1) == "AA"


class TestCommercialCols:
    """Tests for commercial_cols function."""

    def test_returns_price_and_total_columns(self):
        """Should return tuple of (price_col, total_col)."""
        price, total = commercial_cols(6, 1)
        assert price == "F"
        assert total == "G"

    def test_second_slot(self):
        """Second slot should be offset by 2 (width_per_slot=2)."""
        price, total = commercial_cols(6, 2)
        # Slot 2: 6 + (2-1)*2 = 8 => H, I
        assert price == "H"
        assert total == "I"

    def test_multiple_slots(self):
        """Multiple slots should work correctly."""
        # Slot 3: 6 + (3-1)*2 = 10 => J, K
        price, total = commercial_cols(6, 3)
        assert price == "J"
        assert total == "K"

        # Slot 5: 6 + (5-1)*2 = 14 => N, O
        price, total = commercial_cols(6, 5)
        assert price == "N"
        assert total == "O"


class TestSheetColRule:
    """Tests for SheetColRule dataclass."""

    def test_dataclass_creation(self):
        """Should create SheetColRule instances."""
        rule = SheetColRule(start_col_index=5, width_per_slot=2)
        assert rule.start_col_index == 5
        assert rule.width_per_slot == 2

    def test_dataclass_is_frozen(self):
        """SheetColRule should be immutable."""
        rule = SheetColRule(start_col_index=5, width_per_slot=2)
        with pytest.raises(AttributeError):
            rule.start_col_index = 10

    def test_dataclass_equality(self):
        """Equal SheetColRules should be equal."""
        rule1 = SheetColRule(start_col_index=5, width_per_slot=2)
        rule2 = SheetColRule(start_col_index=5, width_per_slot=2)
        assert rule1 == rule2

    def test_dataclass_hashable(self):
        """SheetColRule should be hashable (can be used in sets/dicts)."""
        rule = SheetColRule(start_col_index=5, width_per_slot=2)
        rule_set = {rule}
        assert rule in rule_set
