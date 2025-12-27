"""Tests for SingleMonthDayRangeParser."""

import pytest
from span_parsing.single_month_range_parser import SingleMonthDayRangeParser
from span_parsing.span import Span


class TestSingleMonthDayRangeParser:
    """Test cases for parsing day ranges within a single month."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SingleMonthDayRangeParser()
    
    def test_valid_ad_range(self):
        """Test parsing a valid AD day range."""
        result = self.parser.parse("September 25–28", 2020, False)
        assert result is not None
        assert result.start_year == 2020
        assert result.start_month == 9
        assert result.start_day == 25
        assert result.end_year == 2020
        assert result.end_month == 9
        assert result.end_day == 28
        assert result.is_bc is False
        assert result.precision == "day"
    
    def test_valid_bc_range(self):
        """Test parsing a valid BC day range."""
        result = self.parser.parse("September 25–28", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.start_month == 9
        assert result.start_day == 25
        assert result.end_year == 490
        assert result.end_month == 9
        assert result.end_day == 28
        assert result.is_bc is True
    
    def test_various_dash_styles(self):
        """Test parsing with different dash characters."""
        test_cases = [
            "March 15–20",
            "March 15—20",
            "March 15−20",
            "March 15-20",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 2020, False)
            assert result is not None, f"Failed to parse: {text}"
            assert result.start_day == 15
            assert result.end_day == 20
    
    def test_month_name_case_insensitive(self):
        """Test that month names are case-insensitive."""
        test_cases = [
            "january 15–20",
            "JANUARY 15–20",
            "January 15–20",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 2020, False)
            assert result is not None, f"Failed to parse: {text}"
            assert result.start_month == 1
    
    def test_invalid_month_name(self):
        """Test that invalid month names return None."""
        result = self.parser.parse("Octember 15–20", 2020, False)
        assert result is None
    
    def test_single_digit_days(self):
        """Test parsing with single-digit days."""
        result = self.parser.parse("March 5–8", 2020, False)
        assert result is not None
        assert result.start_day == 5
        assert result.end_day == 8
    
    def test_double_digit_days(self):
        """Test parsing with double-digit days."""
        result = self.parser.parse("March 15–28", 2020, False)
        assert result is not None
        assert result.start_day == 15
        assert result.end_day == 28
    
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
        assert result is not None
        assert result.start_day == 15
        assert result.end_day == 20
    
    def test_whitespace_variations(self):
        """Test parsing with various whitespace patterns."""
        test_cases = [
            "March  15  –  20",
            "March 15–20",
            "March 15 – 20",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 2020, False)
            assert result is not None, f"Failed to parse: {text}"
    
    def test_beginning_of_month(self):
        """Test parsing range at beginning of month."""
        result = self.parser.parse("January 1–5", 2020, False)
        assert result is not None
        assert result.start_day == 1
        assert result.end_day == 5
    
    def test_end_of_month(self):
        """Test parsing range at end of month."""
        result = self.parser.parse("January 28–31", 2020, False)
        assert result is not None
        assert result.start_day == 28
        assert result.end_day == 31
    
    def test_full_month_span(self):
        """Test parsing range spanning most of the month."""
        result = self.parser.parse("March 1–31", 2020, False)
        assert result is not None
        assert result.start_day == 1
        assert result.end_day == 31
    
    def test_all_months(self):
        """Test parsing ranges for all 12 months."""
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        for i, month in enumerate(months, start=1):
            result = self.parser.parse(f"{month} 10–15", 2020, False)
            assert result is not None, f"Failed to parse {month}"
            assert result.start_month == i
