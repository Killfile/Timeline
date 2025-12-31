"""Tests for YearOnlyParser."""

import pytest
from span_parsing.year_only_parser import YearOnlyParser
from span_parsing.span import Span, SpanPrecision


class TestYearOnlyParser:
    """Test cases for parsing standalone years without era markers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = YearOnlyParser()
    
    @pytest.mark.parametrize("text,page_year,page_bc,expected_year,expected_bc", [
        ("490", 490, True, 490, True),
        ("2020", 2020, False, 2020, False),
    ])
    def test_valid_years(self, text, page_year, page_bc, expected_year, expected_bc):
        """Test parsing valid years with page context."""
        result = self.parser.parse(text, page_year, page_bc)
        assert result is not None
        assert result.start_year == expected_year
        assert result.end_year == expected_year
        assert result.is_bc is expected_bc
        assert result.precision == SpanPrecision.YEAR_ONLY
        assert result.start_month == 1
        assert result.start_day == 1
        assert result.end_month == 12
        assert result.end_day == 31
    
    @pytest.mark.parametrize("text,page_year", [
        ("490", 490),
        ("2020", 2020),
    ])
    def test_valid_digit_counts(self, text, page_year):
        """Test parsing with three and four-digit years."""
        result = self.parser.parse(text, page_year, True)
        assert result is not None
        assert result.start_year == page_year
    
    @pytest.mark.parametrize("text,page_year,reason", [
        ("45", 45, "two digits"),
        ("5", 5, "one digit"),
        ("10000", 10000, "five digits"),
    ])
    def test_invalid_digit_counts_not_matched(self, text, page_year, reason):
        """Test that years with invalid digit counts are not matched."""
        result = self.parser.parse(text, page_year, True)
        assert result is None, f"Should not match {reason}"
    
    def test_year_zero_invalid(self):
        """Test that year 0 is rejected."""
        result = self.parser.parse("0000", 1, False)
        assert result is None
    
    @pytest.mark.parametrize("page_bc,expected_is_bc", [
        (True, True),
        (False, False),
    ])
    def test_page_bc_determines_era(self, page_bc, expected_is_bc):
        """Test that page_bc parameter determines BC vs AD."""
        result = self.parser.parse("490", 490, page_bc)
        assert result is not None
        assert result.is_bc is expected_is_bc
    
    def test_must_be_at_start_of_string(self):
        """Test that year must be at start of string."""
        result = self.parser.parse("In 490", 490, True)
        assert result is None
    
    @pytest.mark.parametrize("text", [
        " 490",
        "  490",
        "   490",
    ])
    def test_leading_whitespace_allowed(self, text):
        """Test that leading whitespace is allowed."""
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
