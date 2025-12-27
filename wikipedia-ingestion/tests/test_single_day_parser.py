"""Tests for SingleDayParser."""

import pytest
from span_parsing.single_day_parser import SingleDayParser
from span_parsing.span import Span


class TestSingleDayParser:
    """Test cases for parsing single day dates."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SingleDayParser()
    
    @pytest.mark.parametrize("text,page_year,page_bc,expected_month,expected_day", [
        ("September 25", 2020, False, 9, 25),
        ("September 25", 490, True, 9, 25),
    ])
    def test_valid_dates(self, text, page_year, page_bc, expected_month, expected_day):
        """Test parsing valid single day dates."""
        result = self.parser.parse(text, page_year, page_bc)
        assert result is not None
        assert result.start_year == page_year
        assert result.start_month == expected_month
        assert result.start_day == expected_day
        assert result.end_year == page_year
        assert result.end_month == expected_month
        assert result.end_day == expected_day
        assert result.is_bc is page_bc
        assert result.precision == "day"
    
    @pytest.mark.parametrize("text", [
        "january 15",
        "JANUARY 15",
        "January 15",
    ])
    def test_month_name_case_insensitive(self, text):
        """Test that month names are case-insensitive."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None, f"Failed to parse: {text}"
        assert result.start_month == 1
        assert result.start_day == 15
    
    def test_invalid_month_name(self):
        """Test that invalid month names return None."""
        result = self.parser.parse("Octember 15", 2020, False)
        assert result is None
    
    @pytest.mark.parametrize("text,expected_day", [
        ("March 5", 5),
        ("March 15", 15),
    ])
    def test_various_digit_days(self, text, expected_day):
        """Test parsing with single and double-digit days."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None
        assert result.start_day == expected_day
        assert result.end_day == expected_day
    
    def test_page_year_used(self):
        """Test that the page year is correctly applied."""
        result = self.parser.parse("March 15", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 490
    
    def test_embedded_in_longer_text(self):
        """Test parsing when date is embedded in longer text."""
        result = self.parser.parse("Event on March 15 was significant", 2020, False)
        assert result is not None
        assert result.start_day == 15
    
    def test_with_additional_text_after(self):
        """Test parsing with text after the date."""
        result = self.parser.parse("August 29 – Christian Cross Asterism", 2020, False)
        assert result is not None
        assert result.start_month == 8
        assert result.start_day == 29
    
    @pytest.mark.parametrize("text", [
        "March  15",
        "March 15 ",
        " March 15",
    ])
    def test_whitespace_variations(self, text):
        """Test parsing with various whitespace patterns."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None, f"Failed to parse: {text}"
    
    @pytest.mark.parametrize("text,expected_day", [
        ("January 1", 1),
        ("January 31", 31),
    ])
    def test_first_and_last_day_of_month(self, text, expected_day):
        """Test parsing first and last day of month."""
        result = self.parser.parse(text, 2020, False)
        assert result is not None
        assert result.start_day == expected_day
    
    @pytest.mark.parametrize("month,expected_month_num", [
        ("January", 1), ("February", 2), ("March", 3), ("April", 4),
        ("May", 5), ("June", 6), ("July", 7), ("August", 8),
        ("September", 9), ("October", 10), ("November", 11), ("December", 12),
    ])
    def test_all_months(self, month, expected_month_num):
        """Test parsing dates for all 12 months."""
        result = self.parser.parse(f"{month} 15", 2020, False)
        assert result is not None, f"Failed to parse {month}"
        assert result.start_month == expected_month_num
    
    def test_february_29_leap_year(self):
        """Test parsing February 29 (leap year day)."""
        result = self.parser.parse("February 29", 2020, False)
        assert result is not None
        assert result.start_month == 2
        assert result.start_day == 29
    
    def test_does_not_match_range(self):
        """Test that day ranges don't match this parser (they'd match range parser)."""
        # This will still match the first occurrence "September 25"
        result = self.parser.parse("September 25–28", 2020, False)
        assert result is not None  # It matches "September 25"
        assert result.start_day == 25
        assert result.end_day == 25  # Only single day, not the range
    
    @pytest.mark.parametrize("text,expected_day", [
        ("April 31", 31),
        ("January 32", 32),
    ])
    def test_invalid_days_parsed_but_validation_elsewhere(self, text, expected_day):
        """Test that invalid days are parsed (validation happens elsewhere)."""
        # Parser accepts invalid days; validation should reject them later
        result = self.parser.parse(text, 2020, False)
        assert result is not None  # Parser accepts it
        assert result.start_day == expected_day
        # Note: Day validation is not in the parser, it would be in validation layer
