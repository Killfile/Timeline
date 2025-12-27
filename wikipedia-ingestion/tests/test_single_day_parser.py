"""Tests for SingleDayParser."""

import pytest
from span_parsing.single_day_parser import SingleDayParser
from span_parsing.span import Span


class TestSingleDayParser:
    """Test cases for parsing single day dates."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SingleDayParser()
    
    def test_valid_ad_date(self):
        """Test parsing a valid AD single day."""
        result = self.parser.parse("September 25", 2020, False)
        assert result is not None
        assert result.start_year == 2020
        assert result.start_month == 9
        assert result.start_day == 25
        assert result.end_year == 2020
        assert result.end_month == 9
        assert result.end_day == 25
        assert result.is_bc is False
        assert result.precision == "day"
    
    def test_valid_bc_date(self):
        """Test parsing a valid BC single day."""
        result = self.parser.parse("September 25", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.start_month == 9
        assert result.start_day == 25
        assert result.is_bc is True
    
    def test_month_name_case_insensitive(self):
        """Test that month names are case-insensitive."""
        test_cases = [
            "january 15",
            "JANUARY 15",
            "January 15",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 2020, False)
            assert result is not None, f"Failed to parse: {text}"
            assert result.start_month == 1
            assert result.start_day == 15
    
    def test_invalid_month_name(self):
        """Test that invalid month names return None."""
        result = self.parser.parse("Octember 15", 2020, False)
        assert result is None
    
    def test_single_digit_day(self):
        """Test parsing with single-digit day."""
        result = self.parser.parse("March 5", 2020, False)
        assert result is not None
        assert result.start_day == 5
        assert result.end_day == 5
    
    def test_double_digit_day(self):
        """Test parsing with double-digit day."""
        result = self.parser.parse("March 15", 2020, False)
        assert result is not None
        assert result.start_day == 15
        assert result.end_day == 15
    
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
    
    def test_whitespace_variations(self):
        """Test parsing with various whitespace patterns."""
        test_cases = [
            "March  15",
            "March 15 ",
            " March 15",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 2020, False)
            assert result is not None, f"Failed to parse: {text}"
    
    def test_first_day_of_month(self):
        """Test parsing first day of month."""
        result = self.parser.parse("January 1", 2020, False)
        assert result is not None
        assert result.start_day == 1
    
    def test_last_day_of_month(self):
        """Test parsing last day of month."""
        result = self.parser.parse("January 31", 2020, False)
        assert result is not None
        assert result.start_day == 31
    
    def test_all_months(self):
        """Test parsing dates for all 12 months."""
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        for i, month in enumerate(months, start=1):
            result = self.parser.parse(f"{month} 15", 2020, False)
            assert result is not None, f"Failed to parse {month}"
            assert result.start_month == i
    
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
    
    def test_invalid_day_31_in_april(self):
        """Test that April 31 is parsed (validation happens elsewhere)."""
        # Parser will accept it, validation should reject it
        result = self.parser.parse("April 31", 2020, False)
        assert result is not None  # Parser accepts it
        # Note: Day validation is not in the parser, it would be in validation layer
    
    def test_invalid_day_32(self):
        """Test that day 32 is parsed (validation happens elsewhere)."""
        result = self.parser.parse("January 32", 2020, False)
        assert result is not None  # Parser accepts it
        # Note: Day validation is not in the parser
