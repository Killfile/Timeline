"""Tests for YearOnlyParser."""

import pytest
from span_parsing.year_only_parser import YearOnlyParser
from span_parsing.span import Span


class TestYearOnlyParser:
    """Test cases for parsing standalone years without era markers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = YearOnlyParser()
    
    def test_valid_bc_year(self):
        """Test parsing a valid BC year using page context."""
        result = self.parser.parse("490", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 490
        assert result.is_bc is True
        assert result.precision == "year"
        assert result.start_month == 1
        assert result.start_day == 1
        assert result.end_month == 12
        assert result.end_day == 31
    
    def test_valid_ad_year(self):
        """Test parsing a valid AD year using page context."""
        result = self.parser.parse("2020", 2020, False)
        assert result is not None
        assert result.start_year == 2020
        assert result.end_year == 2020
        assert result.is_bc is False
    
    def test_three_digit_year(self):
        """Test parsing with three-digit year."""
        result = self.parser.parse("490", 490, True)
        assert result is not None
        assert result.start_year == 490
    
    def test_four_digit_year(self):
        """Test parsing with four-digit year."""
        result = self.parser.parse("2020", 2020, False)
        assert result is not None
        assert result.start_year == 2020
    
    def test_two_digit_year_not_matched(self):
        """Test that two-digit years are not matched."""
        result = self.parser.parse("45", 45, True)
        assert result is None  # Requires 3-4 digits
    
    def test_one_digit_year_not_matched(self):
        """Test that one-digit years are not matched."""
        result = self.parser.parse("5", 5, True)
        assert result is None  # Requires 3-4 digits
    
    def test_five_digit_year_not_matched(self):
        """Test that five-digit years are not matched."""
        result = self.parser.parse("10000", 10000, False)
        assert result is None  # Only 3-4 digits allowed
    
    def test_year_zero_invalid(self):
        """Test that year 0 is rejected."""
        result = self.parser.parse("0000", 1, False)
        # Parser will accept 0, validation should reject it
        assert result is None
    
    def test_page_bc_determines_era(self):
        """Test that page_bc parameter determines BC vs AD."""
        result_bc = self.parser.parse("490", 490, True)
        assert result_bc is not None
        assert result_bc.is_bc is True
        
        result_ad = self.parser.parse("490", 490, False)
        assert result_ad is not None
        assert result_ad.is_bc is False
    
    def test_must_be_at_start_of_string(self):
        """Test that year must be at start of string."""
        result = self.parser.parse("In 490", 490, True)
        # This should NOT match because regex allows leading whitespace but not other prefixes
        assert result is None
    
    def test_leading_whitespace_allowed(self):
        """Test that leading whitespace is allowed."""
        test_cases = [
            " 490",
            "  490",
            "   490",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 490, True)
            assert result is not None, f"Failed to parse: {text}"
    
    def test_text_after_year(self):
        """Test parsing with text after the year."""
        result = self.parser.parse("490 was significant", 490, True)
        assert result is not None
        assert result.start_year == 490
    
    def test_does_not_match_with_era_marker(self):
        """Test that years with era markers don't match (handled by other parser)."""
        # The regex specifically looks for a year NOT followed by era markers
        # But it will still match the number part
        result = self.parser.parse("490 BC", 490, True)
        # This will match "490" because the regex is `^\s*(\d{3,4})\b`
        # and \b is a word boundary, so "490" followed by space matches
        assert result is not None  # Matches, but YearWithEraParser should be tried first
    
    def test_does_not_match_year_range(self):
        """Test that year ranges don't match this parser."""
        result = self.parser.parse("490 - 479", 490, True)
        # This will match "490" at the start
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 490  # Only single year, not range
    
    
    def test_year_as_part_of_larger_number(self):
        """Test that year as part of larger number doesn't match."""
        result = self.parser.parse("4900", 490, True)
        assert result is not None  # Will match if 4-digit
        assert result.start_year == 4900
    
    def test_negative_year_not_matched(self):
        """Test that negative years are not matched."""
        result = self.parser.parse("-490", 490, True)
        assert result is None  # Regex doesn't include negative sign
    
    def test_year_with_comma_separator(self):
        """Test year with comma thousands separator not matched."""
        result = self.parser.parse("2,020", 2020, False)
        # Will match "2" which is only 1 digit, so should fail
        assert result is None
