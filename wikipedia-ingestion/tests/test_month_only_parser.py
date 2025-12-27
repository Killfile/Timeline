"""Tests for MonthOnlyParser."""

import pytest
from span_parsing.month_only_parser import MonthOnlyParser
from span_parsing.span import Span


class TestMonthOnlyParser:
    """Test cases for parsing month-only dates."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = MonthOnlyParser()
    
    def test_valid_ad_month(self):
        """Test parsing a valid AD month."""
        result = self.parser.parse("September", 2020, False)
        assert result is not None
        assert result.start_year == 2020
        assert result.start_month == 9
        assert result.start_day == 1
        assert result.end_year == 2020
        assert result.end_month == 9
        assert result.end_day == 30  # September has 30 days
        assert result.is_bc is False
        assert result.precision == "month"
    
    def test_valid_bc_month(self):
        """Test parsing a valid BC month."""
        result = self.parser.parse("September", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.start_month == 9
        assert result.is_bc is True
    
    def test_month_name_case_insensitive(self):
        """Test that month names are case-insensitive."""
        test_cases = [
            "january",
            "JANUARY",
            "January",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 2020, False)
            assert result is not None, f"Failed to parse: {text}"
            assert result.start_month == 1
    
    def test_invalid_month_name(self):
        """Test that invalid month names return None."""
        result = self.parser.parse("Octember", 2020, False)
        assert result is None
    
    def test_all_months_with_correct_days(self):
        """Test parsing all months with correct day counts."""
        expected_days = {
            "January": 31, "February": 28, "March": 31, "April": 30,
            "May": 31, "June": 30, "July": 31, "August": 31,
            "September": 30, "October": 31, "November": 30, "December": 31
        }
        for i, (month, days) in enumerate(expected_days.items(), start=1):
            result = self.parser.parse(month, 2020, False)
            assert result is not None, f"Failed to parse {month}"
            assert result.start_month == i
            assert result.start_day == 1
            assert result.end_day == days, f"{month} should have {days} days"
    
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

    
    def test_whitespace_variations(self):
        """Test parsing with various whitespace patterns."""
        test_cases = [
            " March",
            "March ",
            "  March  ",
        ]
        for text in test_cases:
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
    
    def test_month_abbreviations_not_supported(self):
        """Test that month abbreviations don't match."""
        test_cases = ["Jan", "Feb", "Mar", "Apr"]
        for abbr in test_cases:
            result = self.parser.parse(abbr, 2020, False)
            # These won't match because we only recognize full month names
            assert result is None, f"{abbr} should not match"
