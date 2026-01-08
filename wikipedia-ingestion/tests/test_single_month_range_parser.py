"""Tests for SingleMonthDayRangeParser."""

import pytest
from span_parsing.single_month_range_parser import SingleMonthDayRangeParser
from span_parsing.span import Span, SpanPrecision


class TestSingleMonthDayRangeParser:
    """Test cases for parsing day ranges within a single month."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SingleMonthDayRangeParser()
    
    @pytest.mark.parametrize("text,page_year,page_bc,expected_month,expected_start_day,expected_end_day,expected_is_bc", [
        ("September 25–28", 2020, False, 9, 25, 28, False),
        ("September 25–28", 490, True, 9, 25, 28, True),
    ])
    def test_valid_ranges(self, text, page_year, page_bc, expected_month, expected_start_day, expected_end_day, expected_is_bc):
        """Test parsing valid day ranges in AD and BC."""
        result = self.parser.parse(text, page_year, page_bc)
        assert result is not None
        assert result.start_year == page_year
        assert result.start_month == expected_month
        assert result.start_day == expected_start_day
        assert result.end_year == page_year
        assert result.end_month == expected_month
        assert result.end_day == expected_end_day
        assert result.is_bc is expected_is_bc
        assert result.precision == SpanPrecision.EXACT
    
    @pytest.mark.parametrize("text", [
        "March 15–20",
        "March 15—20",
        "March 15−20",
        "March 15-20",
    ])
    def test_various_dash_styles(self, text):
        """Test parsing with different dash characters."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None, f"Failed to parse: {text}"
        assert result.start_day == 15
        assert result.end_day == 20
    
    @pytest.mark.parametrize("text", [
        "january 15–20",
        "JANUARY 15–20",
        "January 15–20",
    ])
    def test_month_name_case_insensitive(self, text):
        """Test that month names are case-insensitive."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None, f"Failed to parse: {text}"
        assert result.start_month == 1
    
    def test_invalid_month_name(self):
        """Test that invalid month names return None."""
        result = self.parser.parse("Octember 15–20", 2020, False)
        assert result is None
    
    @pytest.mark.parametrize("text,expected_start,expected_end", [
        ("March 5–8", 5, 8),
        ("March 15–28", 15, 28),
    ])
    def test_various_digit_days(self, text, expected_start, expected_end):
        """Test parsing with single and double-digit days."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None
        assert result.start_day == expected_start
        assert result.end_day == expected_end
    
    def test_reversed_day_order_invalid(self):
        """Test that reversed day order is rejected by validation."""
        result = self.parser.parse("March 28–15", 2020, False)
        assert result is None  # Should fail validation
    
    def test_page_year_used(self):
        """Test that the page year is correctly applied."""
        result = self.parser.parse("March 15–20", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 490
    
    def test_embedded_in_longer_text(self):
        """Test parsing when date is embedded in longer text."""
        result = self.parser.parse("Event from March 15–20 was significant", 2020, False)
        assert result is  None
    
    @pytest.mark.parametrize("text", [
        "March  15  –  20",
        "March 15–20",
        "March 15 – 20",
    ])
    def test_whitespace_variations(self, text):
        """Test parsing with various whitespace patterns."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None, f"Failed to parse: {text}"
    
    @pytest.mark.parametrize("text,expected_start,expected_end", [
        ("January 1–5", 1, 5),
        ("January 28–31", 28, 31),
        ("March 1–31", 1, 31),
    ])
    def test_month_boundary_ranges(self, text, expected_start, expected_end):
        """Test parsing ranges at beginning, end, and spanning full month."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None
        assert result.start_day == expected_start
        assert result.end_day == expected_end
    
    @pytest.mark.parametrize("month,expected_month_num", [
        ("January", 1), ("February", 2), ("March", 3), ("April", 4),
        ("May", 5), ("June", 6), ("July", 7), ("August", 8),
        ("September", 9), ("October", 10), ("November", 11), ("December", 12),
    ])
    def test_all_months(self, month, expected_month_num):
        """Test parsing ranges for all 12 months."""
        result = self.parser.parse(f"{month} 10–15", 2020, False)
        assert result is not None, f"Failed to parse {month}"
        assert result.start_month == expected_month_num
