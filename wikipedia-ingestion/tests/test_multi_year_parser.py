"""Tests for MultiYearMonthAndDayRangeParser."""

import pytest
from span_parsing.multi_year_parser import MultiYearMonthAndDayRangeParser
from span_parsing.span import Span


class TestMultiYearMonthAndDayRangeParser:
    """Test cases for parsing date ranges across multiple years."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = MultiYearMonthAndDayRangeParser()
    
    def test_valid_ad_range(self):
        """Test parsing a valid AD date range across years."""
        result = self.parser.parse("September 28, 2020 – October 2, 2021", 2020, False)
        assert result is not None
        assert result.start_year == 2020
        assert result.start_month == 9
        assert result.start_day == 28
        assert result.end_year == 2021
        assert result.end_month == 10
        assert result.end_day == 2
        assert result.is_bc is False
        assert result.precision == "day"
    
    def test_valid_bc_range(self):
        """Test parsing a valid BC date range across years."""
        result = self.parser.parse("December 28, 498 - January 2, 491", 490, page_bc=True)
        assert result is not None
        assert result.start_year == 498
        assert result.start_month == 12
        assert result.start_day == 28
        assert result.end_year == 491
        assert result.end_month == 1
        assert result.end_day == 2
        assert result.is_bc is True
        assert result.precision == "day"
    
    def test_various_dash_styles(self):
        """Test parsing with different dash characters."""
        test_cases = [
            "March 15, 2019 – April 20, 2020",
            "March 15, 2019 — April 20, 2020",
            "March 15, 2019 − April 20, 2020",
            "March 15, 2019 - April 20, 2020",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 2019, False)
            assert result is not None, f"Failed to parse: {text}"
            assert result.start_year == 2019
            assert result.end_year == 2020
    
    def test_month_name_case_insensitive(self):
        """Test that month names are case-insensitive."""
        test_cases = [
            "january 15, 2020 – february 20, 2021",
            "JANUARY 15, 2020 – FEBRUARY 20, 2021",
            "January 15, 2020 – February 20, 2021",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 2020, False)
            assert result is not None, f"Failed to parse: {text}"
            assert result.start_month == 1
            assert result.end_month == 2
    
    def test_invalid_month_name(self):
        """Test that invalid month names return None."""
        result = self.parser.parse("Octember 15, 2020 – November 20, 2021", 2020, False)
        assert result is None
    
    def test_single_digit_days(self):
        """Test parsing with single-digit days."""
        result = self.parser.parse("March 5, 2020 – April 8, 2021", 2020, False)
        assert result is not None
        assert result.start_day == 5
        assert result.end_day == 8
    
    def test_double_digit_days(self):
        """Test parsing with double-digit days."""
        result = self.parser.parse("March 15, 2020 – April 28, 2021", 2020, False)
        assert result is not None
        assert result.start_day == 15
        assert result.end_day == 28
    
    def test_reversed_date_order_invalid(self):
        """Test that reversed date order is rejected by validation."""
        result = self.parser.parse("December 31, 2021 – January 1, 2020", 2020, False)
        assert result is None  # Should fail validation
    
    def test_year_zero_invalid(self):
        """Test that year 0 is rejected."""
        result = self.parser.parse("December 31, 0001 – January 1, 0000", 1, False)
        assert result is None
    
    def test_does_not_match_single_year(self):
        """Test that single year dates don't match this parser."""
        result = self.parser.parse("September 28 – October 2", 2020, False)
        assert result is None
    
    def test_does_not_match_year_only(self):
        """Test that year-only dates don't match this parser."""
        result = self.parser.parse("2020 – 2021", 2020, False)
        assert result is None
    
    def test_embedded_in_longer_text(self):
        """Test parsing when date is embedded in longer text."""
        result = self.parser.parse("Event from March 15, 2020 – April 20, 2021 was significant", 2020, False)
        assert result is not None
        assert result.start_year == 2020
        assert result.end_year == 2021
    
    def test_whitespace_variations(self):
        """Test parsing with various whitespace patterns."""
        test_cases = [
            "March  15,  2020  –  April  20,  2021",
            "March 15,2020 – April 20,2021",
            "March 15, 2020–April 20, 2021",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 2020, False)
            assert result is not None, f"Failed to parse: {text}"
