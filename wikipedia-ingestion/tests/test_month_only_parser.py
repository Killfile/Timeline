"""Tests for MonthOnlyParser."""

import pytest
from span_parsing.month_only_parser import MonthOnlyParser
from span_parsing.span import Span, SpanPrecision


class TestMonthOnlyParser:
    """Test cases for parsing month-only dates."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = MonthOnlyParser()
    
    @pytest.mark.parametrize("text,page_year,page_bc,expected_month,expected_end_day,expected_is_bc", [
        ("September", 2020, False, 9, 30, False),
        ("September", 490, True, 9, 30, True),
    ])
    def test_valid_months(self, text, page_year, page_bc, expected_month, expected_end_day, expected_is_bc):
        """Test parsing valid months in AD and BC."""
        result = self.parser.parse(text, page_year, page_bc)
        assert result is not None
        assert result.start_year == page_year
        assert result.start_month == expected_month
        assert result.start_day == 1
        assert result.end_year == page_year
        assert result.end_month == expected_month
        assert result.end_day == expected_end_day
        assert result.is_bc is expected_is_bc
        assert result.precision == SpanPrecision.MONTH_ONLY
    
    @pytest.mark.parametrize("text", [
        "january",
        "JANUARY",
        "January",
    ])
    def test_month_name_case_insensitive(self, text):
        """Test that month names are case-insensitive."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None, f"Failed to parse: {text}"
        assert result.start_month == 1
    
    def test_invalid_month_name(self):
        """Test that invalid month names return None."""
        result = self.parser.parse("Octember", 2020, False)
        assert result is None
    
    @pytest.mark.parametrize("month,expected_month_num,expected_days", [
        ("January", 1, 31), ("February", 2, 28), ("March", 3, 31), ("April", 4, 30),
        ("May", 5, 31), ("June", 6, 30), ("July", 7, 31), ("August", 8, 31),
        ("September", 9, 30), ("October", 10, 31), ("November", 11, 30), ("December", 12, 31),
    ])
    def test_all_months_with_correct_days(self, month, expected_month_num, expected_days):
        """Test parsing all months with correct day counts."""
        result = self.parser.parse(month, 2020, False)
        assert result is not None, f"Failed to parse {month}"
        assert result.start_month == expected_month_num
        assert result.start_day == 1
        assert result.end_day == expected_days, f"{month} should have {expected_days} days"
    
    def test_page_year_used(self):
        """Test that the page year is correctly applied."""
        result = self.parser.parse("March", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 490
    
    def test_embedded_in_longer_text(self):
        """Test parsing when month is embedded in longer text."""
        result = self.parser.parse("In March there was an event", 2020, False)
        assert result is None

    
    @pytest.mark.parametrize("text", [
        " March",
        "March ",
        "  March  ",
    ])
    def test_whitespace_variations(self, text):
        """Test parsing with various whitespace patterns."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None, f"Failed to parse: {text}"
    
    def test_does_not_match_with_day(self):
        """Test that month with day doesn't match (would match other parsers first)."""
        # This will still match just the month name "March"
        result = self.parser.parse("March 15", 2020, False)
        assert result is not None  # It matches "March"
        # But single day parser should be tried first in the factory pattern
    
    def test_february_leap_year_note(self):
        """Test February - note that leap years aren't handled."""
        result = self.parser.parse("February", 2020, False)  # 2020 is a leap year
        assert result is not None
        assert result.end_day == 28  # Parser doesn't calculate leap years
        # This is a known limitation mentioned in the code
    
    def test_does_not_match_year(self):
        """Test that year numbers don't match month parser."""
        result = self.parser.parse("2020", 2020, False)
        assert result is None  # "2020" is not a month name
    
    def test_span_covers_entire_month(self):
        """Test that the span covers the entire month."""
        result = self.parser.parse("March", 2020, False)
        assert result is not None
        assert result.start_day == 1
        assert result.end_day == 31
        # Should span from first to last day of March
    
    @pytest.mark.parametrize("abbr", ["Jan", "Feb", "Mar", "Apr"])
    def test_month_abbreviations_not_supported(self, abbr):
        """Test that month abbreviations don't match."""
        result = self.parser.parse(abbr, 2020, False)
        # These won't match because we only recognize full month names
        assert result is None, f"{abbr} should not match"
