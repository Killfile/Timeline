"""Tests for MultiYearMonthAndDayRangeParser."""

import pytest
from span_parsing.multi_year_parser import MultiYearMonthAndDayRangeParser
from span_parsing.span import Span


class TestMultiYearMonthAndDayRangeParser:
    """Test cases for parsing date ranges across multiple years."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = MultiYearMonthAndDayRangeParser()
    
    @pytest.mark.parametrize("text,page_year,page_bc,expected_start_year,expected_start_month,expected_start_day,expected_end_year,expected_end_month,expected_end_day,expected_is_bc", [
        ("September 28, 2020 – October 2, 2021", 2020, False, 2020, 9, 28, 2021, 10, 2, False),
        ("December 28, 498 - January 2, 491", 490, True, 498, 12, 28, 491, 1, 2, True),
    ])
    def test_valid_ranges(self, text, page_year, page_bc, expected_start_year, expected_start_month, expected_start_day, expected_end_year, expected_end_month, expected_end_day, expected_is_bc):
        """Test parsing valid date ranges across years in AD and BC."""
        result = self.parser.parse(text, page_year, page_bc=page_bc)
        assert result is not None
        assert result.start_year == expected_start_year
        assert result.start_month == expected_start_month
        assert result.start_day == expected_start_day
        assert result.end_year == expected_end_year
        assert result.end_month == expected_end_month
        assert result.end_day == expected_end_day
        assert result.is_bc is expected_is_bc
        assert result.precision == "day"
    
    @pytest.mark.parametrize("text", [
        "March 15, 2019 – April 20, 2020",
        "March 15, 2019 — April 20, 2020",
        "March 15, 2019 − April 20, 2020",
        "March 15, 2019 - April 20, 2020",
    ])
    def test_various_dash_styles(self, text):
        """Test parsing with different dash characters."""
        result = self.parser.parse(text, 2019, False)
        assert result is not None, f"Failed to parse: {text}"
        assert result.start_year == 2019
        assert result.end_year == 2020
    
    @pytest.mark.parametrize("text", [
        "january 15, 2020 – february 20, 2021",
        "JANUARY 15, 2020 – FEBRUARY 20, 2021",
        "January 15, 2020 – February 20, 2021",
    ])
    def test_month_name_case_insensitive(self, text):
        """Test that month names are case-insensitive."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None, f"Failed to parse: {text}"
        assert result.start_month == 1
        assert result.end_month == 2
    
    def test_invalid_month_name(self):
        """Test that invalid month names return None."""
        result = self.parser.parse("Octember 15, 2020 – November 20, 2021", 2020, False)
        assert result is None
    
    @pytest.mark.parametrize("text,expected_start_day,expected_end_day", [
        ("March 5, 2020 – April 8, 2021", 5, 8),
        ("March 15, 2020 – April 28, 2021", 15, 28),
    ])
    def test_various_digit_days(self, text, expected_start_day, expected_end_day):
        """Test parsing with single and double-digit days."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None
        assert result.start_day == expected_start_day
        assert result.end_day == expected_end_day
    
    def test_reversed_date_order_invalid(self):
        """Test that reversed date order is rejected by validation."""
        result = self.parser.parse("December 31, 2021 – January 1, 2020", 2020, False)
        assert result is None  # Should fail validation
    
    def test_year_zero_invalid(self):
        """Test that year 0 is rejected."""
        result = self.parser.parse("December 31, 0001 – January 1, 0000", 1, False)
        assert result is None
    
    @pytest.mark.parametrize("text", [
        "September 28 – October 2",
        "2020 – 2021",
    ])
    def test_does_not_match_single_year_or_year_only(self, text):
        """Test that single year dates and year-only dates don't match this parser."""
        result = self.parser.parse(text, 2020, False)
        assert result is None
    
    def test_embedded_in_longer_text(self):
        """Test parsing when date is embedded in longer text."""
        result = self.parser.parse("Event from March 15, 2020 – April 20, 2021 was significant", 2020, False)
        assert result is not None
        assert result.start_year == 2020
        assert result.end_year == 2021
    
    @pytest.mark.parametrize("text", [
        "March  15,  2020  –  April  20,  2021",
        "March 15,2020 – April 20,2021",
        "March 15, 2020–April 20, 2021",
    ])
    def test_whitespace_variations(self, text):
        """Test parsing with various whitespace patterns."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None, f"Failed to parse: {text}"
